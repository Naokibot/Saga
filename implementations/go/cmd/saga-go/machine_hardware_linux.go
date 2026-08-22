//go:build linux

package main

import (
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
	"unsafe"
)

const (
	i2cSlave                   = 0x0703
	i2cTenBit                  = 0x0704
	i2cRdwr                    = 0x0707
	i2cMRead                   = 0x0001
	i2cMTen                    = 0x0010
	canRaw                     = 1
	solCANRaw                  = 101
	canRawFDFrames             = 5
	soTimestamping             = 37
	sofTimestampingRXHardware  = 1 << 2
	sofTimestampingRXSoftware  = 1 << 3
	sofTimestampingSoftware    = 1 << 4
	sofTimestampingRawHardware = 1 << 6
	etherCATEtherType          = 0x88a4
)

const (
	machineCANEFFFlag = uint32(0x80000000)
	machineCANEFFMask = uint32(0x1fffffff)
	machineCANSFFMask = uint32(0x000007ff)
)

type machineI2C struct {
	file    *os.File
	address uint16
}
type i2cMsg struct {
	Addr  uint16
	Flags uint16
	Len   uint16
	Buf   uintptr
}
type i2cRdwrData struct {
	Msgs  uintptr
	Nmsgs uint32
	Pad   uint32
}

type machineSPI struct {
	file  *os.File
	speed uint32
	mode  uint8
	bits  uint8
}
type spiIOCTransfer struct {
	TxBuf          uint64
	RxBuf          uint64
	Len            uint32
	SpeedHz        uint32
	DelayUsecs     uint16
	BitsPerWord    uint8
	CSChange       uint8
	TxNBits        uint8
	RxNBits        uint8
	WordDelayUsecs uint8
	Pad            uint8
}

type machineUART struct {
	file    *os.File
	timeout time.Duration
}
type machineCAN struct {
	fd           int
	fdMode       bool
	timestamping bool
}

type machineEtherCAT struct {
	fd          int
	ifindex     int
	source      [6]byte
	destination [6]byte
}

func machineHTons(v uint16) uint16 { return v<<8 | v>>8 }

func machineNetworkTimestamp(oob []byte) (int64, string) {
	msgs, err := syscall.ParseSocketControlMessage(oob)
	if err == nil {
		for _, msg := range msgs {
			if msg.Header.Level != syscall.SOL_SOCKET || (msg.Header.Type != soTimestamping && msg.Header.Type != 65) || len(msg.Data) < 48 {
				continue
			}
			sec0 := int64(binary.LittleEndian.Uint64(msg.Data[0:8]))
			ns0 := int64(binary.LittleEndian.Uint64(msg.Data[8:16]))
			sec2 := int64(binary.LittleEndian.Uint64(msg.Data[32:40]))
			ns2 := int64(binary.LittleEndian.Uint64(msg.Data[40:48]))
			if sec2 != 0 || ns2 != 0 {
				return sec2*1_000_000_000 + ns2, "hardware"
			}
			if sec0 != 0 || ns0 != 0 {
				return sec0*1_000_000_000 + ns0, "software"
			}
		}
	}
	return time.Now().UnixNano(), "host"
}

type machinePWM struct {
	path   string
	period int64
	closed bool
}
type machineServo struct {
	pwm                          *machinePWM
	minUS, maxUS, minDeg, maxDeg float64
	safety                       *MachineSafety
}

func (s *machineServo) stop() error {
	return s.pwm.setDuty(0)
}
func (s *machineServo) sagaMachineClose() error { return s.stop() }

type machineMotor struct {
	forward, reverse *machinePWM
	deadband         float64
	safety           *MachineSafety
	command          float64
}

func (m *machineMotor) sagaMachineClose() error { return m.stop() }
func (m *machineMotor) stop() error {
	if err := m.forward.setDuty(0); err != nil {
		return err
	}
	if err := m.reverse.setDuty(0); err != nil {
		return err
	}
	m.command = 0
	return nil
}

func (m *machineMotor) write(command float64) error {
	if !finiteFloat(command) {
		return fmt.Errorf("motor command must be finite")
	}
	if m.safety != nil {
		tripped, reason := m.safety.snapshot()
		if tripped {
			_ = m.stop()
			return fmt.Errorf("motor output blocked by safety latch: %s", reason)
		}
	}
	command = clampFloat(command, -1, 1)
	if math.Abs(command) <= m.deadband {
		command = 0
	}
	// Break-before-make prevents both H-bridge legs from being driven together.
	if err := m.forward.setDuty(0); err != nil {
		return err
	}
	if err := m.reverse.setDuty(0); err != nil {
		return err
	}
	if command > 0 {
		if err := m.forward.setDuty(command); err != nil {
			return err
		}
	} else if command < 0 {
		if err := m.reverse.setDuty(-command); err != nil {
			return err
		}
	}
	m.command = command
	return nil
}

func ioctl(fd uintptr, req uintptr, arg uintptr) error {
	_, _, e := syscall.Syscall(syscall.SYS_IOCTL, fd, req, arg)
	if e != 0 {
		return e
	}
	return nil
}
func iocWrite(typ, nr, size uintptr) uintptr {
	const nrShift = 0
	const typeShift = 8
	const sizeShift = 16
	const dirShift = 30
	const write = 1
	return uintptr(write<<dirShift) | (typ << typeShift) | (nr << nrShift) | (size << sizeShift)
}

func openI2C(path string, address int) (*machineI2C, error) {
	if address < 0 || address > 0x3ff {
		return nil, fmt.Errorf("I2C address must be 0..0x3ff")
	}
	f, e := os.OpenFile(path, os.O_RDWR, 0)
	if e != nil {
		return nil, e
	}
	if address > 0x7f {
		if e = ioctl(f.Fd(), i2cTenBit, 1); e != nil {
			f.Close()
			return nil, e
		}
	}
	if e = ioctl(f.Fd(), i2cSlave, uintptr(address)); e != nil {
		f.Close()
		return nil, e
	}
	return &machineI2C{file: f, address: uint16(address)}, nil
}
func (d *machineI2C) sagaMachineClose() error { return d.close() }
func (d *machineI2C) close() error {
	if d.file == nil {
		return nil
	}
	e := d.file.Close()
	d.file = nil
	return e
}
func (d *machineI2C) write(b []byte) error {
	if d.file == nil {
		return fmt.Errorf("I2C device closed")
	}
	n, e := d.file.Write(b)
	if e == nil && n != len(b) {
		e = io.ErrShortWrite
	}
	return e
}
func (d *machineI2C) read(n int) ([]byte, error) {
	if d.file == nil {
		return nil, fmt.Errorf("I2C device closed")
	}
	if n < 0 {
		return nil, fmt.Errorf("I2C read count must be >= 0")
	}
	b := make([]byte, n)
	if n == 0 {
		return b, nil
	}
	_, e := io.ReadFull(d.file, b)
	return b, e
}
func (d *machineI2C) writeRead(out []byte, n int) ([]byte, error) {
	if d.file == nil {
		return nil, fmt.Errorf("I2C device closed")
	}
	if n < 0 {
		return nil, fmt.Errorf("I2C read count must be >= 0")
	}
	if len(out) > 0xffff || n > 0xffff {
		return nil, fmt.Errorf("I2C combined-transfer segments must be <= 65535 bytes")
	}
	in := make([]byte, n)
	msgs := make([]i2cMsg, 2)
	flags := uint16(0)
	if d.address > 0x7f {
		flags = i2cMTen
	}
	if len(out) > 0 {
		msgs[0] = i2cMsg{Addr: d.address, Flags: flags, Len: uint16(len(out)), Buf: uintptr(unsafe.Pointer(&out[0]))}
	} else {
		msgs[0] = i2cMsg{Addr: d.address, Flags: flags}
	}
	if n > 0 {
		msgs[1] = i2cMsg{Addr: d.address, Flags: flags | i2cMRead, Len: uint16(n), Buf: uintptr(unsafe.Pointer(&in[0]))}
	} else {
		msgs[1] = i2cMsg{Addr: d.address, Flags: flags | i2cMRead}
	}
	data := i2cRdwrData{Msgs: uintptr(unsafe.Pointer(&msgs[0])), Nmsgs: 2}
	if e := ioctl(d.file.Fd(), i2cRdwr, uintptr(unsafe.Pointer(&data))); e != nil {
		return nil, e
	}
	return in, nil
}

func openSPI(path string, speed, mode, bits int) (*machineSPI, error) {
	if speed <= 0 {
		return nil, fmt.Errorf("SPI speed_hz must be > 0")
	}
	if mode < 0 || mode > 3 {
		return nil, fmt.Errorf("SPI mode must be 0..3")
	}
	if bits < 1 || bits > 32 {
		return nil, fmt.Errorf("SPI bits_per_word must be 1..32")
	}
	f, e := os.OpenFile(path, os.O_RDWR, 0)
	if e != nil {
		return nil, e
	}
	d := &machineSPI{file: f, speed: uint32(speed), mode: uint8(mode), bits: uint8(bits)}
	if e = ioctl(f.Fd(), iocWrite('k', 1, 1), uintptr(unsafe.Pointer(&d.mode))); e != nil {
		f.Close()
		return nil, e
	}
	if e = ioctl(f.Fd(), iocWrite('k', 3, 1), uintptr(unsafe.Pointer(&d.bits))); e != nil {
		f.Close()
		return nil, e
	}
	if e = ioctl(f.Fd(), iocWrite('k', 4, 4), uintptr(unsafe.Pointer(&d.speed))); e != nil {
		f.Close()
		return nil, e
	}
	return d, nil
}
func (d *machineSPI) sagaMachineClose() error { return d.close() }
func (d *machineSPI) close() error {
	if d.file == nil {
		return nil
	}
	e := d.file.Close()
	d.file = nil
	return e
}
func (d *machineSPI) transfer(out []byte) ([]byte, error) {
	if d.file == nil {
		return nil, fmt.Errorf("SPI device closed")
	}
	if len(out) == 0 {
		return []byte{}, nil
	}
	in := make([]byte, len(out))
	tr := spiIOCTransfer{TxBuf: uint64(uintptr(unsafe.Pointer(&out[0]))), RxBuf: uint64(uintptr(unsafe.Pointer(&in[0]))), Len: uint32(len(out)), SpeedHz: d.speed, BitsPerWord: d.bits}
	if e := ioctl(d.file.Fd(), iocWrite('k', 0, unsafe.Sizeof(tr)), uintptr(unsafe.Pointer(&tr))); e != nil {
		return nil, e
	}
	return in, nil
}

func baudConstant(baud int) (uint32, bool) {
	switch baud {
	case 1200:
		return syscall.B1200, true
	case 2400:
		return syscall.B2400, true
	case 4800:
		return syscall.B4800, true
	case 9600:
		return syscall.B9600, true
	case 19200:
		return syscall.B19200, true
	case 38400:
		return syscall.B38400, true
	case 57600:
		return syscall.B57600, true
	case 115200:
		return syscall.B115200, true
	case 230400:
		return syscall.B230400, true
	}
	return 0, false
}
func openUART(path string, baud, timeoutMS int) (*machineUART, error) {
	b, ok := baudConstant(baud)
	if !ok {
		return nil, fmt.Errorf("unsupported UART baud rate: %d", baud)
	}
	if timeoutMS < 0 {
		return nil, fmt.Errorf("UART timeout_ms must be >= 0")
	}
	fd, e := syscall.Open(path, syscall.O_RDWR|syscall.O_NOCTTY|syscall.O_CLOEXEC, 0)
	if e != nil {
		return nil, e
	}
	f := os.NewFile(uintptr(fd), path)
	var t syscall.Termios
	if e = ioctl(f.Fd(), syscall.TCGETS, uintptr(unsafe.Pointer(&t))); e != nil {
		f.Close()
		return nil, e
	}
	t.Iflag = 0
	t.Oflag = 0
	t.Lflag = 0
	t.Cflag = syscall.CLOCAL | syscall.CREAD | syscall.CS8 | b
	t.Cc[syscall.VMIN] = 0
	t.Cc[syscall.VTIME] = 0
	if e = ioctl(f.Fd(), syscall.TCSETS, uintptr(unsafe.Pointer(&t))); e != nil {
		f.Close()
		return nil, e
	}
	return &machineUART{file: f, timeout: time.Duration(timeoutMS) * time.Millisecond}, nil
}
func (d *machineUART) sagaMachineClose() error { return d.close() }
func (d *machineUART) close() error {
	if d.file == nil {
		return nil
	}
	e := d.file.Close()
	d.file = nil
	return e
}
func (d *machineUART) write(b []byte) error {
	if d.file == nil {
		return fmt.Errorf("UART device closed")
	}
	for len(b) > 0 {
		n, e := d.file.Write(b)
		if e != nil {
			return e
		}
		if n <= 0 {
			return io.ErrShortWrite
		}
		b = b[n:]
	}
	return nil
}
func (d *machineUART) read(max int) ([]byte, error) {
	if d.file == nil {
		return nil, fmt.Errorf("UART device closed")
	}
	if max < 0 {
		return nil, fmt.Errorf("UART max_bytes must be >= 0")
	}
	if max == 0 {
		return []byte{}, nil
	}
	fd := int(d.file.Fd())
	var set syscall.FdSet
	set.Bits[fd/64] |= 1 << uint(fd%64)
	tv := syscall.NsecToTimeval(d.timeout.Nanoseconds())
	n, e := syscall.Select(fd+1, &set, nil, nil, &tv)
	if e != nil {
		return nil, e
	}
	if n == 0 {
		return []byte{}, nil
	}
	b := make([]byte, max)
	n, e = syscall.Read(fd, b)
	return b[:machineMaxInt(n, 0)], e
}
func machineMaxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func bindCAN(fd int, iface string) error {
	ifc, e := net.InterfaceByName(iface)
	if e != nil {
		return e
	}
	type sockaddrCAN struct {
		Family  uint16
		Pad     uint16
		Ifindex int32
		Addr    [8]byte
	}
	sa := sockaddrCAN{Family: syscall.AF_CAN, Ifindex: int32(ifc.Index)}
	_, _, errno := syscall.Syscall(syscall.SYS_BIND, uintptr(fd), uintptr(unsafe.Pointer(&sa)), unsafe.Sizeof(sa))
	if errno != 0 {
		return errno
	}
	return nil
}
func openCAN(iface string, fdMode bool) (*machineCAN, error) {
	fd, e := syscall.Socket(syscall.AF_CAN, syscall.SOCK_RAW|syscall.SOCK_CLOEXEC, canRaw)
	if e != nil {
		return nil, e
	}
	if fdMode {
		if e = syscall.SetsockoptInt(fd, solCANRaw, canRawFDFrames, 1); e != nil {
			syscall.Close(fd)
			return nil, e
		}
	}
	if e = bindCAN(fd, iface); e != nil {
		syscall.Close(fd)
		return nil, e
	}
	return &machineCAN{fd: fd, fdMode: fdMode}, nil
}
func (d *machineCAN) sagaMachineClose() error { return d.close() }
func (d *machineCAN) close() error {
	if d.fd < 0 {
		return nil
	}
	e := syscall.Close(d.fd)
	d.fd = -1
	return e
}
func (d *machineCAN) enableTimestamping(hardwarePreferred bool) error {
	flags := sofTimestampingRXSoftware | sofTimestampingSoftware
	if hardwarePreferred {
		flags |= sofTimestampingRXHardware | sofTimestampingRawHardware
	}
	if err := syscall.SetsockoptInt(d.fd, syscall.SOL_SOCKET, soTimestamping, flags); err != nil {
		return err
	}
	d.timestamping = true
	return nil
}
func (d *machineCAN) send(id int, data []byte) error { return d.sendFlags(id, data, 0) }
func (d *machineCAN) sendFlags(id int, data []byte, fdFlags byte) error {
	if d.fd < 0 {
		return fmt.Errorf("CAN device closed")
	}
	if id < 0 || id > 0x1fffffff {
		return fmt.Errorf("CAN id must be 0..0x1fffffff")
	}
	limit := 8
	if d.fdMode {
		limit = 64
	}
	if len(data) > limit {
		return fmt.Errorf("CAN payload exceeds %d bytes", limit)
	}
	size := 16
	if d.fdMode {
		size = 72
	}
	buf := make([]byte, size)
	wireID := uint32(id)
	if id > int(machineCANSFFMask) {
		wireID |= machineCANEFFFlag
	}
	binary.LittleEndian.PutUint32(buf[0:4], wireID)
	buf[4] = byte(len(data))
	if fdFlags & ^byte(0x03) != 0 {
		return fmt.Errorf("unsupported CAN FD flags")
	}
	if fdFlags != 0 && !d.fdMode {
		return fmt.Errorf("CAN FD flags require fd_mode")
	}
	if d.fdMode {
		buf[5] = fdFlags
	}
	copy(buf[8:], data)
	n, e := syscall.Write(d.fd, buf)
	if e == nil && n != len(buf) {
		return io.ErrShortWrite
	}
	return e
}
func (d *machineCAN) recv(timeoutMS int) (machineCANFrame, error) {
	if d.fd < 0 {
		return machineCANFrame{}, fmt.Errorf("CAN device closed")
	}
	if timeoutMS < 0 {
		return machineCANFrame{}, fmt.Errorf("CAN timeout_ms must be >= 0")
	}
	var set syscall.FdSet
	set.Bits[d.fd/64] |= 1 << uint(d.fd%64)
	tv := syscall.NsecToTimeval((time.Duration(timeoutMS) * time.Millisecond).Nanoseconds())
	n, e := syscall.Select(d.fd+1, &set, nil, nil, &tv)
	if e != nil {
		return machineCANFrame{}, e
	}
	if n == 0 {
		return machineCANFrame{received: false}, nil
	}
	size := 16
	if d.fdMode {
		size = 72
	}
	buf := make([]byte, size)
	n, e = syscall.Read(d.fd, buf)
	if e != nil {
		return machineCANFrame{}, e
	}
	if n < 16 {
		return machineCANFrame{}, io.ErrUnexpectedEOF
	}
	ln := int(buf[4])
	limit := 8
	if d.fdMode {
		limit = 64
	}
	if ln > limit || 8+ln > n {
		return machineCANFrame{}, fmt.Errorf("invalid CAN frame length")
	}
	wireID := binary.LittleEndian.Uint32(buf[:4])
	mask := machineCANSFFMask
	if wireID&machineCANEFFFlag != 0 {
		mask = machineCANEFFMask
	}
	flags := byte(0)
	if n == 72 {
		flags = buf[5]
	}
	return machineCANFrame{received: true, id: int(wireID & mask), data: append([]byte(nil), buf[8:8+ln]...), flags: flags}, nil
}

func (d *machineCAN) recvTimestamped(timeoutMS int) (machineCANFrame, error) {
	if d.fd < 0 {
		return machineCANFrame{}, fmt.Errorf("CAN device closed")
	}
	if !d.fdMode {
		return machineCANFrame{}, fmt.Errorf("CAN FD receive requires fd_mode")
	}
	if timeoutMS < 0 {
		return machineCANFrame{}, fmt.Errorf("CAN timeout_ms must be >= 0")
	}
	var set syscall.FdSet
	set.Bits[d.fd/64] |= 1 << uint(d.fd%64)
	tv := syscall.NsecToTimeval((time.Duration(timeoutMS) * time.Millisecond).Nanoseconds())
	n, e := syscall.Select(d.fd+1, &set, nil, nil, &tv)
	if e != nil {
		return machineCANFrame{}, e
	}
	if n == 0 {
		return machineCANFrame{received: false}, nil
	}
	buf := make([]byte, 72)
	oob := make([]byte, 256)
	n, oobn, _, _, e := syscall.Recvmsg(d.fd, buf, oob, 0)
	if e != nil {
		return machineCANFrame{}, e
	}
	if n != 72 {
		return machineCANFrame{}, fmt.Errorf("expected CAN FD frame, got %d bytes", n)
	}
	ln := int(buf[4])
	if ln > 64 || 8+ln > n {
		return machineCANFrame{}, fmt.Errorf("invalid CAN FD frame length")
	}
	wireID := binary.LittleEndian.Uint32(buf[:4])
	mask := machineCANSFFMask
	if wireID&machineCANEFFFlag != 0 {
		mask = machineCANEFFMask
	}
	ts, source := time.Now().UnixNano(), "host"
	if d.timestamping {
		ts, source = machineNetworkTimestamp(oob[:oobn])
	}
	return machineCANFrame{received: true, id: int(wireID & mask), data: append([]byte(nil), buf[8:8+ln]...), flags: buf[5], timestampNS: ts, timestampSource: source}, nil
}

func openEtherCAT(ifaceName string, destination []byte, hardwareTimestamps bool) (*machineEtherCAT, error) {
	if len(destination) != 6 {
		return nil, fmt.Errorf("EtherCAT destination MAC must contain 6 bytes")
	}
	iface, e := net.InterfaceByName(ifaceName)
	if e != nil {
		return nil, e
	}
	if len(iface.HardwareAddr) < 6 {
		return nil, fmt.Errorf("EtherCAT interface has no 6-byte MAC address")
	}
	proto := machineHTons(etherCATEtherType)
	fd, e := syscall.Socket(syscall.AF_PACKET, syscall.SOCK_RAW|syscall.SOCK_CLOEXEC, int(proto))
	if e != nil {
		return nil, e
	}
	sa := &syscall.SockaddrLinklayer{Protocol: proto, Ifindex: iface.Index}
	if e = syscall.Bind(fd, sa); e != nil {
		syscall.Close(fd)
		return nil, e
	}
	d := &machineEtherCAT{fd: fd, ifindex: iface.Index}
	copy(d.source[:], iface.HardwareAddr[:6])
	copy(d.destination[:], destination)
	flags := sofTimestampingRXSoftware | sofTimestampingSoftware
	if hardwareTimestamps {
		flags |= sofTimestampingRXHardware | sofTimestampingRawHardware
	}
	if e = syscall.SetsockoptInt(fd, syscall.SOL_SOCKET, soTimestamping, flags); e != nil {
		syscall.Close(fd)
		return nil, e
	}
	return d, nil
}
func (d *machineEtherCAT) sagaMachineClose() error { return d.close() }
func (d *machineEtherCAT) close() error {
	if d.fd < 0 {
		return nil
	}
	e := syscall.Close(d.fd)
	d.fd = -1
	return e
}
func (d *machineEtherCAT) exchange(payload []byte, timeoutMS int) (string, error) {
	if d.fd < 0 {
		return "", fmt.Errorf("EtherCAT device closed")
	}
	if timeoutMS < 0 {
		return "", fmt.Errorf("EtherCAT timeout_ms must be >= 0")
	}
	frame := make([]byte, 14+len(payload))
	copy(frame[0:6], d.destination[:])
	copy(frame[6:12], d.source[:])
	binary.BigEndian.PutUint16(frame[12:14], etherCATEtherType)
	copy(frame[14:], payload)
	var addr [8]uint8
	copy(addr[:6], d.destination[:])
	sa := &syscall.SockaddrLinklayer{Protocol: machineHTons(etherCATEtherType), Ifindex: d.ifindex, Halen: 6, Addr: addr}
	if e := syscall.Sendto(d.fd, frame, 0, sa); e != nil {
		return "", e
	}
	deadline := time.Now().Add(time.Duration(timeoutMS) * time.Millisecond)
	for {
		remaining := time.Until(deadline)
		if remaining < 0 {
			return "", fmt.Errorf("EtherCAT exchange timed out")
		}
		var set syscall.FdSet
		set.Bits[d.fd/64] |= 1 << uint(d.fd%64)
		tv := syscall.NsecToTimeval(remaining.Nanoseconds())
		n, e := syscall.Select(d.fd+1, &set, nil, nil, &tv)
		if e != nil {
			return "", e
		}
		if n == 0 {
			return "", fmt.Errorf("EtherCAT exchange timed out")
		}
		buf := make([]byte, 65535)
		oob := make([]byte, 256)
		rn, oobn, _, from, e := syscall.Recvmsg(d.fd, buf, oob, 0)
		if e != nil {
			return "", e
		}
		if ll, ok := from.(*syscall.SockaddrLinklayer); ok && ll.Pkttype == 4 {
			continue
		}
		if rn < 14 || binary.BigEndian.Uint16(buf[12:14]) != etherCATEtherType {
			continue
		}
		ts, source := machineNetworkTimestamp(oob[:oobn])
		body := map[string]any{"frame_hex": hex.EncodeToString(buf[14:rn]), "timestamp_ns": ts, "timestamp_source": source}
		j, _ := json.Marshal(body)
		return string(j), nil
	}
}

func openPWM(chip, channel int, periodNS int64) (*machinePWM, error) {
	if chip < 0 || channel < 0 {
		return nil, fmt.Errorf("PWM chip/channel must be >= 0")
	}
	if periodNS <= 0 {
		return nil, fmt.Errorf("PWM period_ns must be > 0")
	}
	root := filepath.Join("/sys/class/pwm", "pwmchip"+strconv.Itoa(chip))
	path := filepath.Join(root, "pwm"+strconv.Itoa(channel))
	if _, e := os.Stat(path); os.IsNotExist(e) {
		if e = os.WriteFile(filepath.Join(root, "export"), []byte(strconv.Itoa(channel)), 0644); e != nil {
			return nil, e
		}
		deadline := time.Now().Add(time.Second)
		for time.Now().Before(deadline) {
			if _, e = os.Stat(path); e == nil {
				break
			}
			time.Sleep(10 * time.Millisecond)
		}
	}
	if _, e := os.Stat(path); e != nil {
		return nil, e
	}
	d := &machinePWM{path: path, period: periodNS}
	if e := d.writeFile("enable", "0"); e != nil {
		return nil, e
	}
	if e := d.writeFile("period", strconv.FormatInt(periodNS, 10)); e != nil {
		return nil, e
	}
	if e := d.writeFile("duty_cycle", "0"); e != nil {
		return nil, e
	}
	return d, nil
}
func (d *machinePWM) writeFile(name, value string) error {
	if d.closed {
		return fmt.Errorf("PWM channel is closed")
	}
	return os.WriteFile(filepath.Join(d.path, name), []byte(value), 0644)
}
func (d *machinePWM) setDuty(v float64) error {
	if !finiteFloat(v) || v < 0 || v > 1 {
		return fmt.Errorf("PWM duty must be in 0..1")
	}
	n := int64(mathRound(v * float64(d.period)))
	if n < 0 {
		n = 0
	}
	if n > d.period {
		n = d.period
	}
	return d.writeFile("duty_cycle", strconv.FormatInt(n, 10))
}
func mathRound(v float64) float64 {
	if v < 0 {
		return float64(int64(v - 0.5))
	}
	return float64(int64(v + 0.5))
}
func (d *machinePWM) enable() error           { return d.writeFile("enable", "1") }
func (d *machinePWM) disable() error          { return d.writeFile("enable", "0") }
func (d *machinePWM) close() error            { return d.disable() }
func (d *machinePWM) sagaMachineClose() error { return d.close() }

type machineModbusRTU struct {
	uart   *machineUART
	unit   byte
	closed bool
	mu     sync.Mutex
}

func openMachineModbusRTU(path string, baud, timeoutMS, unit int) (*machineModbusRTU, error) {
	if unit < 1 || unit > 247 {
		return nil, fmt.Errorf("Modbus RTU unit_id must be 1..247")
	}
	if timeoutMS <= 0 {
		return nil, fmt.Errorf("Modbus RTU timeout_ms must be > 0")
	}
	uart, err := openUART(path, baud, timeoutMS)
	if err != nil {
		return nil, err
	}
	return &machineModbusRTU{uart: uart, unit: byte(unit)}, nil
}

func (d *machineModbusRTU) readResponse(expected int, function byte) ([]byte, error) {
	target := expected
	deadline := time.Now().Add(d.uart.timeout)
	buf := make([]byte, 0, target)
	for len(buf) < target {
		part, err := d.uart.read(target - len(buf))
		if err != nil {
			return nil, err
		}
		if len(part) > 0 {
			buf = append(buf, part...)
			if len(buf) >= 2 && buf[1] == function|0x80 {
				target = 5
			}
		}
		if !time.Now().Before(deadline) {
			break
		}
	}
	if len(buf) != target {
		return nil, fmt.Errorf("Modbus RTU timeout/short response: %d/%d bytes", len(buf), target)
	}
	return buf, nil
}
func (d *machineModbusRTU) transact(function byte, data []byte, expected int) ([]byte, error) {
	if d.closed {
		return nil, fmt.Errorf("Modbus RTU master is closed")
	}
	d.mu.Lock()
	defer d.mu.Unlock()
	body := append([]byte{d.unit, function}, data...)
	crc := machineModbusCRC16(body)
	request := append(body, byte(crc), byte(crc>>8))
	if err := d.uart.write(request); err != nil {
		return nil, err
	}
	resp, err := d.readResponse(expected, function)
	if err != nil {
		return nil, err
	}
	if resp[0] != d.unit {
		return nil, fmt.Errorf("Modbus RTU response unit id mismatch")
	}
	wire := binary.LittleEndian.Uint16(resp[len(resp)-2:])
	if machineModbusCRC16(resp[:len(resp)-2]) != wire {
		return nil, fmt.Errorf("Modbus RTU CRC mismatch")
	}
	return resp[1 : len(resp)-2], nil
}
func (d *machineModbusRTU) readHolding(address, count int) ([]Value, error) {
	a, e := machineModbusU16("Modbus address", address)
	if e != nil {
		return nil, e
	}
	c, e := machineModbusCount("Modbus register count", count, 125)
	if e != nil {
		return nil, e
	}
	req := make([]byte, 4)
	binary.BigEndian.PutUint16(req, a)
	binary.BigEndian.PutUint16(req[2:], uint16(c))
	p, e := d.transact(3, req, 5+2*c)
	if e != nil {
		return nil, e
	}
	return machineParseRegisters(3, p, c)
}
func (d *machineModbusRTU) readInput(address, count int) ([]Value, error) {
	a, e := machineModbusU16("Modbus address", address)
	if e != nil {
		return nil, e
	}
	c, e := machineModbusCount("Modbus register count", count, 125)
	if e != nil {
		return nil, e
	}
	req := make([]byte, 4)
	binary.BigEndian.PutUint16(req, a)
	binary.BigEndian.PutUint16(req[2:], uint16(c))
	p, e := d.transact(4, req, 5+2*c)
	if e != nil {
		return nil, e
	}
	return machineParseRegisters(4, p, c)
}
func (d *machineModbusRTU) readCoils(address, count int) ([]Value, error) {
	a, e := machineModbusU16("Modbus address", address)
	if e != nil {
		return nil, e
	}
	c, e := machineModbusCount("Modbus coil count", count, 2000)
	if e != nil {
		return nil, e
	}
	req := make([]byte, 4)
	binary.BigEndian.PutUint16(req, a)
	binary.BigEndian.PutUint16(req[2:], uint16(c))
	p, e := d.transact(1, req, 5+(c+7)/8)
	if e != nil {
		return nil, e
	}
	return machineParseCoils(1, p, c)
}
func (d *machineModbusRTU) writeRegister(address, value int) error {
	a, e := machineModbusU16("Modbus address", address)
	if e != nil {
		return e
	}
	v, e := machineModbusU16("Modbus register value", value)
	if e != nil {
		return e
	}
	req := make([]byte, 4)
	binary.BigEndian.PutUint16(req, a)
	binary.BigEndian.PutUint16(req[2:], v)
	p, e := d.transact(6, req, 8)
	if e != nil {
		return e
	}
	if len(p) >= 2 && p[0] == 0x86 {
		return machineModbusException(6, p[0], p[1])
	}
	if len(p) != 5 || p[0] != 6 || !equalBytes(p[1:], req) {
		return fmt.Errorf("malformed Modbus write-register response")
	}
	return nil
}
func (d *machineModbusRTU) writeRegisters(address int, values []int) error {
	a, e := machineModbusU16("Modbus address", address)
	if e != nil {
		return e
	}
	if len(values) < 1 || len(values) > 123 {
		return fmt.Errorf("Modbus register values must contain 1..123 entries")
	}
	req := make([]byte, 5+2*len(values))
	binary.BigEndian.PutUint16(req, a)
	binary.BigEndian.PutUint16(req[2:], uint16(len(values)))
	req[4] = byte(2 * len(values))
	for j, v := range values {
		q, e := machineModbusU16("Modbus register value", v)
		if e != nil {
			return e
		}
		binary.BigEndian.PutUint16(req[5+2*j:], q)
	}
	p, e := d.transact(0x10, req, 8)
	if e != nil {
		return e
	}
	if len(p) >= 2 && p[0] == 0x90 {
		return machineModbusException(0x10, p[0], p[1])
	}
	if len(p) != 5 || p[0] != 0x10 || binary.BigEndian.Uint16(p[1:3]) != a || binary.BigEndian.Uint16(p[3:5]) != uint16(len(values)) {
		return fmt.Errorf("malformed Modbus write-multiple response")
	}
	return nil
}
func (d *machineModbusRTU) writeCoil(address int, state bool) error {
	a, e := machineModbusU16("Modbus address", address)
	if e != nil {
		return e
	}
	req := make([]byte, 4)
	binary.BigEndian.PutUint16(req, a)
	if state {
		binary.BigEndian.PutUint16(req[2:], 0xff00)
	}
	p, e := d.transact(5, req, 8)
	if e != nil {
		return e
	}
	if len(p) >= 2 && p[0] == 0x85 {
		return machineModbusException(5, p[0], p[1])
	}
	if len(p) != 5 || p[0] != 5 || !equalBytes(p[1:], req) {
		return fmt.Errorf("malformed Modbus write-coil response")
	}
	return nil
}
func (d *machineModbusRTU) sagaMachineClose() error {
	if d.closed {
		return nil
	}
	d.closed = true
	return d.uart.close()
}

func machineHardwareCall(name string, args []Value) (Value, error) {
	switch name {
	case "modbus_rtu_open":
		path, e := machineText(args[0], "path")
		if e != nil {
			return nil, e
		}
		baud, e := machineInt(args[1], "baud")
		if e != nil {
			return nil, e
		}
		timeout, e := machineInt(args[2], "timeout_ms")
		if e != nil {
			return nil, e
		}
		unit, e := machineInt(args[3], "unit_id")
		if e != nil {
			return nil, e
		}
		return openMachineModbusRTU(path, baud, timeout, unit)
	case "i2c_open":
		path, e := machineText(args[0], "path")
		if e != nil {
			return nil, e
		}
		addr, e := machineInt(args[1], "address")
		if e != nil {
			return nil, e
		}
		return openI2C(path, addr)
	case "i2c_write":
		d, ok := args[0].(*machineI2C)
		if !ok {
			return nil, fmt.Errorf("I2C handle required")
		}
		b, e := machineBytes(args[1], "data")
		if e != nil {
			return nil, e
		}
		return nil, d.write(b)
	case "i2c_read":
		d, ok := args[0].(*machineI2C)
		if !ok {
			return nil, fmt.Errorf("I2C handle required")
		}
		n, e := machineInt(args[1], "count")
		if e != nil {
			return nil, e
		}
		return d.read(n)
	case "i2c_write_read":
		d, ok := args[0].(*machineI2C)
		if !ok {
			return nil, fmt.Errorf("I2C handle required")
		}
		b, e := machineBytes(args[1], "data")
		if e != nil {
			return nil, e
		}
		n, e := machineInt(args[2], "count")
		if e != nil {
			return nil, e
		}
		return d.writeRead(b, n)
	case "i2c_close":
		d, ok := args[0].(*machineI2C)
		if !ok {
			return nil, fmt.Errorf("I2C handle required")
		}
		return nil, d.close()
	case "spi_open":
		path, e := machineText(args[0], "path")
		if e != nil {
			return nil, e
		}
		speed, _ := machineInt(args[1], "speed_hz")
		mode, _ := machineInt(args[2], "mode")
		bits, _ := machineInt(args[3], "bits_per_word")
		return openSPI(path, speed, mode, bits)
	case "spi_transfer":
		d, ok := args[0].(*machineSPI)
		if !ok {
			return nil, fmt.Errorf("SPI handle required")
		}
		b, e := machineBytes(args[1], "data")
		if e != nil {
			return nil, e
		}
		return d.transfer(b)
	case "spi_close":
		d, ok := args[0].(*machineSPI)
		if !ok {
			return nil, fmt.Errorf("SPI handle required")
		}
		return nil, d.close()
	case "uart_open":
		path, e := machineText(args[0], "path")
		if e != nil {
			return nil, e
		}
		baud, _ := machineInt(args[1], "baud")
		timeout, _ := machineInt(args[2], "timeout_ms")
		return openUART(path, baud, timeout)
	case "uart_write":
		d, ok := args[0].(*machineUART)
		if !ok {
			return nil, fmt.Errorf("UART handle required")
		}
		b, e := machineBytes(args[1], "data")
		if e != nil {
			return nil, e
		}
		return nil, d.write(b)
	case "uart_read":
		d, ok := args[0].(*machineUART)
		if !ok {
			return nil, fmt.Errorf("UART handle required")
		}
		n, e := machineInt(args[1], "max_bytes")
		if e != nil {
			return nil, e
		}
		return d.read(n)
	case "uart_close":
		d, ok := args[0].(*machineUART)
		if !ok {
			return nil, fmt.Errorf("UART handle required")
		}
		return nil, d.close()
	case "can_open":
		iface, e := machineText(args[0], "interface")
		if e != nil {
			return nil, e
		}
		fdMode, e := parseMachineBool(args[1], "fd_mode")
		if e != nil {
			return nil, e
		}
		return openCAN(iface, fdMode)
	case "can_send":
		d, ok := args[0].(*machineCAN)
		if !ok {
			return nil, fmt.Errorf("CAN handle required")
		}
		id, e := machineInt(args[1], "id")
		if e != nil {
			return nil, e
		}
		b, e := machineBytes(args[2], "data")
		if e != nil {
			return nil, e
		}
		return nil, d.send(id, b)
	case "can_recv":
		d, ok := args[0].(*machineCAN)
		if !ok {
			return nil, fmt.Errorf("CAN handle required")
		}
		ms, e := machineInt(args[1], "timeout_ms")
		if e != nil {
			return nil, e
		}
		return d.recv(ms)
	case "can_timestamping":
		d, ok := args[0].(*machineCAN)
		if !ok {
			return nil, fmt.Errorf("CAN handle required")
		}
		hardwarePreferred, e := parseMachineBool(args[1], "hardware_preferred")
		if e != nil {
			return nil, e
		}
		return nil, d.enableTimestamping(hardwarePreferred)
	case "canfd_send":
		d, ok := args[0].(*machineCAN)
		if !ok {
			return nil, fmt.Errorf("CAN handle required")
		}
		if !d.fdMode {
			return nil, fmt.Errorf("CAN FD send requires fd_mode")
		}
		id, e := machineInt(args[1], "id")
		if e != nil {
			return nil, e
		}
		b, e := machineBytes(args[2], "data")
		if e != nil {
			return nil, e
		}
		brs, e := parseMachineBool(args[3], "brs")
		if e != nil {
			return nil, e
		}
		flags := byte(0)
		if brs {
			flags |= 0x01
		}
		return nil, d.sendFlags(id, b, flags)
	case "canfd_recv":
		d, ok := args[0].(*machineCAN)
		if !ok {
			return nil, fmt.Errorf("CAN handle required")
		}
		ms, e := machineInt(args[1], "timeout_ms")
		if e != nil {
			return nil, e
		}
		f, e := d.recvTimestamped(ms)
		if e != nil {
			return nil, e
		}
		body := map[string]any{
			"received":         f.received,
			"id":               f.id,
			"data_hex":         hex.EncodeToString(f.data),
			"brs":              f.flags&0x01 != 0,
			"esi":              f.flags&0x02 != 0,
			"timestamp_ns":     f.timestampNS,
			"timestamp_source": f.timestampSource,
		}
		if !f.received {
			body["timestamp_ns"] = int64(0)
			body["timestamp_source"] = "none"
		}
		j, _ := json.Marshal(body)
		return string(j), nil
	case "can_close":
		d, ok := args[0].(*machineCAN)
		if !ok {
			return nil, fmt.Errorf("CAN handle required")
		}
		return nil, d.close()
	case "ethercat_open":
		iface, e := machineText(args[0], "interface")
		if e != nil {
			return nil, e
		}
		destination, e := machineBytes(args[1], "destination_mac")
		if e != nil {
			return nil, e
		}
		hardwareTimestamps, e := parseMachineBool(args[2], "hardware_timestamps")
		if e != nil {
			return nil, e
		}
		return openEtherCAT(iface, destination, hardwareTimestamps)
	case "ethercat_exchange":
		d, ok := args[0].(*machineEtherCAT)
		if !ok {
			return nil, fmt.Errorf("EtherCAT handle required")
		}
		payload, e := machineBytes(args[1], "frame")
		if e != nil {
			return nil, e
		}
		ms, e := machineInt(args[2], "timeout_ms")
		if e != nil {
			return nil, e
		}
		return d.exchange(payload, ms)
	case "ethercat_close":
		d, ok := args[0].(*machineEtherCAT)
		if !ok {
			return nil, fmt.Errorf("EtherCAT handle required")
		}
		return nil, d.close()
	case "pwm_open":
		chip, _ := machineInt(args[0], "chip")
		channel, _ := machineInt(args[1], "channel")
		period, _ := machineInt(args[2], "period_ns")
		return openPWM(chip, channel, int64(period))
	case "pwm_write":
		d, ok := args[0].(*machinePWM)
		if !ok {
			return nil, fmt.Errorf("PWM handle required")
		}
		q, e := machineNumber(args[1], "duty")
		if e != nil {
			return nil, e
		}
		return nil, d.setDuty(q)
	case "pwm_enable":
		d, ok := args[0].(*machinePWM)
		if !ok {
			return nil, fmt.Errorf("PWM handle required")
		}
		return nil, d.enable()
	case "pwm_disable":
		d, ok := args[0].(*machinePWM)
		if !ok {
			return nil, fmt.Errorf("PWM handle required")
		}
		return nil, d.disable()
	case "pwm_close":
		d, ok := args[0].(*machinePWM)
		if !ok {
			return nil, fmt.Errorf("PWM handle required")
		}
		return nil, d.close()
	case "servo":
		p, ok := args[0].(*machinePWM)
		if !ok {
			return nil, fmt.Errorf("PWM handle required")
		}
		v := make([]float64, 4)
		for j := 0; j < 4; j++ {
			q, e := machineNumber(args[j+1], "servo argument")
			if e != nil {
				return nil, e
			}
			v[j] = q
		}
		if v[0] >= v[1] || v[2] >= v[3] {
			return nil, fmt.Errorf("servo ranges must be increasing")
		}
		return &machineServo{pwm: p, minUS: v[0], maxUS: v[1], minDeg: v[2], maxDeg: v[3]}, nil
	case "servo_write":
		s, ok := args[0].(*machineServo)
		if !ok {
			return nil, fmt.Errorf("servo handle required")
		}
		if s.safety != nil {
			tripped, reason := s.safety.snapshot()
			if tripped {
				_ = s.stop()
				return nil, fmt.Errorf("servo output blocked by safety latch: %s", reason)
			}
		}
		deg, e := machineNumber(args[1], "degrees")
		if e != nil {
			return nil, e
		}
		duty, e := machineServoDuty(deg, s.minDeg, s.maxDeg, s.minUS, s.maxUS, float64(s.pwm.period)/1000)
		if e != nil {
			return nil, e
		}
		return nil, s.pwm.setDuty(duty)
	case "servo_guard":
		s, ok := args[0].(*machineServo)
		if !ok {
			return nil, fmt.Errorf("servo handle required")
		}
		latch, ok := args[1].(*MachineSafety)
		if !ok {
			return nil, fmt.Errorf("safety latch required")
		}
		s.safety = latch
		if err := latch.registerStop(s.stop); err != nil {
			return nil, err
		}
		return nil, nil
	case "motor":
		fwd, ok := args[0].(*machinePWM)
		if !ok {
			return nil, fmt.Errorf("forward PWM handle required")
		}
		rev, ok := args[1].(*machinePWM)
		if !ok {
			return nil, fmt.Errorf("reverse PWM handle required")
		}
		deadband, e := machineNumber(args[2], "deadband")
		if e != nil {
			return nil, e
		}
		if deadband < 0 || deadband >= 1 {
			return nil, fmt.Errorf("motor deadband must be in 0..1")
		}
		latch, ok := args[3].(*MachineSafety)
		if !ok {
			return nil, fmt.Errorf("safety latch required")
		}
		motor := &machineMotor{forward: fwd, reverse: rev, deadband: deadband, safety: latch}
		if err := latch.registerStop(motor.stop); err != nil {
			return nil, err
		}
		return motor, nil
	case "motor_write":
		m, ok := args[0].(*machineMotor)
		if !ok {
			return nil, fmt.Errorf("motor handle required")
		}
		command, e := machineNumber(args[1], "command")
		if e != nil {
			return nil, e
		}
		return nil, m.write(command)
	case "motor_stop":
		m, ok := args[0].(*machineMotor)
		if !ok {
			return nil, fmt.Errorf("motor handle required")
		}
		return nil, m.stop()
	case "motor_command":
		m, ok := args[0].(*machineMotor)
		if !ok {
			return nil, fmt.Errorf("motor handle required")
		}
		return machineNumberFromFloat(m.command), nil
	case "iio_read":
		path, e := machineText(args[0], "path")
		if e != nil {
			return nil, e
		}
		scale, e := machineNumber(args[1], "scale")
		if e != nil {
			return nil, e
		}
		clean, e := filepath.Abs(path)
		if e != nil {
			return nil, e
		}
		root := "/sys/bus/iio/devices"
		resolved, e := filepath.EvalSymlinks(clean)
		if e != nil {
			return nil, e
		}
		rel, e := filepath.Rel(root, resolved)
		if e != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(os.PathSeparator)) || filepath.IsAbs(rel) {
			return nil, fmt.Errorf("iio_read is restricted to /sys/bus/iio/devices")
		}
		raw, e := os.ReadFile(resolved)
		if e != nil {
			return nil, e
		}
		f, e := strconv.ParseFloat(string(bytesTrimSpace(raw)), 64)
		if e != nil {
			return nil, e
		}
		return numberFromFloat64(f * scale), nil
	}
	return nil, fmt.Errorf("unknown machine hardware operation %s", name)
}
func bytesTrimSpace(b []byte) []byte {
	for len(b) > 0 && (b[0] == ' ' || b[0] == '\n' || b[0] == '\r' || b[0] == '\t') {
		b = b[1:]
	}
	for len(b) > 0 && (b[len(b)-1] == ' ' || b[len(b)-1] == '\n' || b[len(b)-1] == '\r' || b[len(b)-1] == '\t') {
		b = b[:len(b)-1]
	}
	return b
}
