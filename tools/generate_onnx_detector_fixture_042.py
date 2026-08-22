#!/usr/bin/env python3
"""Generate the tiny, deterministic ONNX object-detector fixture used by Saga 0.42.

This intentionally avoids depending on the onnx Python package.  It builds the small
subset of the official ONNX protobuf schema that this fixture needs, then emits an
actual ONNX graph consumed by OpenCV DNN in qualification tests.
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory


def _build_model_bytes() -> bytes:
    fd = descriptor_pb2.FileDescriptorProto(name="saga_tiny_onnx.proto", package="onnx", syntax="proto3")

    def msg(name):
        m = fd.message_type.add(); m.name = name; return m

    def field(m, name, num, typ, label=1, type_name=None, oneof=None, packed=None):
        f = m.field.add(); f.name = name; f.number = num; f.type = typ; f.label = label
        if type_name: f.type_name = type_name
        if oneof is not None: f.oneof_index = oneof
        if packed is not None: f.options.packed = packed
        return f

    shape = msg("TensorShapeProto"); dim = shape.nested_type.add(); dim.name = "Dimension"; dim.oneof_decl.add().name = "value"
    field(dim, "dim_value", 1, 3, oneof=0); field(dim, "dim_param", 2, 9, oneof=0)
    field(shape, "dim", 1, 11, label=3, type_name=".onnx.TensorShapeProto.Dimension")
    tp = msg("TypeProto"); ten = tp.nested_type.add(); ten.name = "Tensor"; field(ten, "elem_type", 1, 5); field(ten, "shape", 2, 11, type_name=".onnx.TensorShapeProto")
    tp.oneof_decl.add().name = "value"; field(tp, "tensor_type", 1, 11, type_name=".onnx.TypeProto.Tensor", oneof=0)
    vi = msg("ValueInfoProto"); field(vi, "name", 1, 9); field(vi, "type", 2, 11, type_name=".onnx.TypeProto")
    tensor = msg("TensorProto"); field(tensor, "dims", 1, 3, label=3, packed=True); field(tensor, "data_type", 2, 5); field(tensor, "name", 8, 9); field(tensor, "raw_data", 9, 12)
    node = msg("NodeProto"); field(node, "input", 1, 9, label=3); field(node, "output", 2, 9, label=3); field(node, "name", 3, 9); field(node, "op_type", 4, 9); field(node, "domain", 7, 9)
    graph = msg("GraphProto"); field(graph, "node", 1, 11, label=3, type_name=".onnx.NodeProto"); field(graph, "name", 2, 9); field(graph, "initializer", 5, 11, label=3, type_name=".onnx.TensorProto"); field(graph, "input", 11, 11, label=3, type_name=".onnx.ValueInfoProto"); field(graph, "output", 12, 11, label=3, type_name=".onnx.ValueInfoProto")
    opset = msg("OperatorSetIdProto"); field(opset, "domain", 1, 9); field(opset, "version", 2, 3)
    model = msg("ModelProto"); field(model, "ir_version", 1, 3); field(model, "producer_name", 2, 9); field(model, "graph", 7, 11, type_name=".onnx.GraphProto"); field(model, "opset_import", 8, 11, label=3, type_name=".onnx.OperatorSetIdProto")

    pool = descriptor_pool.DescriptorPool(); pool.Add(fd)
    Model = message_factory.GetMessageClass(pool.FindMessageTypeByName("onnx.ModelProto"))
    m = Model(); m.ir_version = 8; m.producer_name = "Saga 0.42 qualification"
    op = m.opset_import.add(); op.domain = ""; op.version = 13
    g = m.graph; g.name = "tiny_brightness_object_detector"
    for name, operator, inputs, outputs in [
        ("gap", "GlobalAveragePool", ["image"], ["pool"]),
        ("flat", "Flatten", ["pool"], ["flat"]),
        ("head", "Gemm", ["flat", "W", "B"], ["detections"]),
    ]:
        n = g.node.add(); n.name = name; n.op_type = operator; n.input.extend(inputs); n.output.extend(outputs)

    weights = [0.0] * 18
    for row in range(3): weights[row * 6 + 4] = 2.0
    bias = [8.0, 8.0, 24.0, 24.0, -3.0, 0.0]
    for name, dims, values in [("W", [3, 6], weights), ("B", [6], bias)]:
        t = g.initializer.add(); t.name = name; t.data_type = 1; t.dims.extend(dims)
        t.raw_data = struct.pack("<" + "f" * len(values), *values)

    def value_info(collection, name, dims):
        v = collection.add(); v.name = name; v.type.tensor_type.elem_type = 1
        for size in dims: v.type.tensor_type.shape.dim.add().dim_value = size

    value_info(g.input, "image", [1, 3, 32, 32])
    value_info(g.output, "detections", [1, 6])
    return m.SerializeToString()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="tests/fixtures/tiny_object_detector.onnx")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = Path(args.output)
    if not out.is_absolute(): out = root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = _build_model_bytes(); out.write_bytes(payload)
    print(f"wrote {out} ({len(payload)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
