from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
PROPOSER_TYPES = {
    "national_body",
    "committee_secretariat",
    "committee",
    "category_a_liaison",
    "technical_management_board",
    "chief_executive_officer",
}
COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class StandardsError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temp = Path(handle.name)
    os.replace(temp, path)


def _require_text(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise StandardsError(f"{label} は空にできません")
    return value


def _country(value: str) -> str:
    result = value.strip().upper()
    if not COUNTRY_RE.fullmatch(result):
        raise StandardsError("country はISO 3166-1 alpha-2形式（例: JP）で指定してください")
    return result


def _email(value: str) -> str:
    result = value.strip()
    if not EMAIL_RE.fullmatch(result):
        raise StandardsError("有効なメールアドレスを指定してください")
    return result


@dataclass(slots=True)
class StandardsRegistry:
    root: Path

    @classmethod
    def open(cls, root: str | Path) -> "StandardsRegistry":
        return cls(Path(root).expanduser().resolve())

    @property
    def registry_file(self) -> Path:
        return self.root / "registry.json"

    @property
    def event_file(self) -> Path:
        return self.root / "events.jsonl"

    @property
    def evidence_dir(self) -> Path:
        return self.root / "evidence"

    def init(self, project: str = "Saga Programming Language") -> None:
        if self.registry_file.exists():
            raise StandardsError(f"既に初期化されています: {self.root}")
        self.root.mkdir(parents=True, exist_ok=True)
        value = {
            "schema_version": SCHEMA_VERSION,
            "project": _require_text(project, "project"),
            "created_at": _utc_now(),
            "proposer": None,
            "project_leader": None,
            "experts": [],
            "p_member_commitments": [],
            "adoptions": [],
            "implementations": [],
            "independent_labs": [],
            "market_evidence": [],
        }
        _atomic_json(self.registry_file, value)
        self._event("registry.initialized", {"project": project})

    def load(self) -> dict[str, Any]:
        if not self.registry_file.exists():
            raise StandardsError(f"標準化レジストリがありません。先に init を実行してください: {self.root}")
        value = json.loads(self.registry_file.read_text(encoding="utf-8"))
        if value.get("schema_version") != SCHEMA_VERSION:
            raise StandardsError("未対応の標準化レジストリ形式です")
        return value

    def save(self, value: dict[str, Any]) -> None:
        _atomic_json(self.registry_file, value)

    def _event(self, kind: str, payload: dict[str, Any]) -> None:
        previous = "0" * 64
        if self.event_file.exists():
            lines = [line for line in self.event_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            if lines:
                previous = json.loads(lines[-1])["hash"]
        event = {"time": _utc_now(), "kind": kind, "payload": payload, "previous": previous}
        event["hash"] = _sha256_bytes(_canonical(event))
        self.event_file.parent.mkdir(parents=True, exist_ok=True)
        with self.event_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    def _store_evidence(self, source: str | Path, label: str) -> dict[str, str]:
        path = Path(source).expanduser().resolve()
        if not path.is_file():
            raise StandardsError(f"{label}の証拠ファイルが見つかりません: {path}")
        data = path.read_bytes()
        digest = _sha256_bytes(data)
        suffix = path.suffix.lower()[:16]
        destination = self.evidence_dir / f"{digest}{suffix}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copyfile(path, destination)
        return {
            "sha256": digest,
            "stored": str(destination.relative_to(self.root)),
            "original_name": path.name,
            "bytes": str(len(data)),
        }

    def set_proposer(self, *, name: str, proposer_type: str, country: str, evidence: str | Path) -> None:
        proposer_type = proposer_type.strip()
        if proposer_type not in PROPOSER_TYPES:
            raise StandardsError(f"proposer-type は次のいずれかです: {', '.join(sorted(PROPOSER_TYPES))}")
        record = {
            "name": _require_text(name, "name"),
            "type": proposer_type,
            "country": _country(country),
            "evidence": self._store_evidence(evidence, "提案資格"),
            "recorded_at": _utc_now(),
        }
        value = self.load(); value["proposer"] = record; self.save(value)
        self._event("proposer.set", {"name": record["name"], "type": proposer_type, "country": record["country"], "evidence": record["evidence"]["sha256"]})

    def nominate_leader(self, *, name: str, email: str, organization: str, country: str, consent: str | Path) -> None:
        record = {
            "name": _require_text(name, "name"),
            "email": _email(email),
            "organization": _require_text(organization, "organization"),
            "country": _country(country),
            "consent": self._store_evidence(consent, "Project Leader本人同意"),
            "nominated_at": _utc_now(),
            "status": "nominated_with_consent",
        }
        value = self.load(); value["project_leader"] = record; self.save(value)
        self._event("project_leader.nominated", {"name": record["name"], "organization": record["organization"], "country": record["country"], "consent": record["consent"]["sha256"]})

    def add_expert(self, *, name: str, email: str, organization: str, country: str, expertise: str, consent: str | Path) -> None:
        record = {
            "id": _sha256_bytes(f"{email.lower()}|{organization}|{country}".encode())[:16],
            "name": _require_text(name, "name"),
            "email": _email(email),
            "organization": _require_text(organization, "organization"),
            "country": _country(country),
            "expertise": _require_text(expertise, "expertise"),
            "consent": self._store_evidence(consent, "専門家本人同意"),
            "joined_at": _utc_now(),
        }
        value = self.load()
        if any(item["id"] == record["id"] for item in value["experts"]):
            raise StandardsError("同じ専門家は既に登録されています")
        value["experts"].append(record); self.save(value)
        self._event("expert.added", {"id": record["id"], "organization": record["organization"], "country": record["country"], "consent": record["consent"]["sha256"]})

    def add_p_member_commitment(self, *, national_body: str, country: str, expert_emails: list[str], evidence: str | Path) -> None:
        value = self.load()
        normalized = [_email(item) for item in expert_emails]
        known = {item["email"] for item in value["experts"]}
        missing = sorted(set(normalized) - known)
        if missing:
            raise StandardsError(f"先に専門家を登録してください: {', '.join(missing)}")
        record = {
            "national_body": _require_text(national_body, "national_body"),
            "country": _country(country),
            "expert_emails": sorted(set(normalized)),
            "evidence": self._store_evidence(evidence, "Pメンバー参加表明"),
            "recorded_at": _utc_now(),
        }
        if any(item["country"] == record["country"] for item in value["p_member_commitments"]):
            raise StandardsError("同じ国のPメンバー参加表明は既に登録されています")
        value["p_member_commitments"].append(record); self.save(value)
        self._event("p_member.commitment_added", {"national_body": record["national_body"], "country": record["country"], "evidence": record["evidence"]["sha256"]})

    def add_adoption(self, *, organization: str, country: str, use_case: str, evidence: str | Path) -> None:
        record = {
            "organization": _require_text(organization, "organization"),
            "country": _country(country),
            "use_case": _require_text(use_case, "use_case"),
            "evidence": self._store_evidence(evidence, "利用実績"),
            "recorded_at": _utc_now(),
        }
        value = self.load(); value["adoptions"].append(record); self.save(value)
        self._event("adoption.added", {"organization": record["organization"], "country": record["country"], "evidence": record["evidence"]["sha256"]})

    def add_implementation(
        self, *, name: str, language: str, repository: str,
        conformance_report: str | Path, independent_from: str = "saga-python",
        level: str = "experimental",
    ) -> None:
        if level not in {"experimental", "core", "full"}:
            raise StandardsError("level は experimental、core、full のいずれかです")
        record = {
            "name": _require_text(name, "name"),
            "implementation_language": _require_text(language, "language"),
            "repository": _require_text(repository, "repository"),
            "independent_from": _require_text(independent_from, "independent_from"),
            "conformance_level": level,
            "conformance_report": self._store_evidence(conformance_report, "適合性レポート"),
            "recorded_at": _utc_now(),
        }
        value = self.load(); value["implementations"].append(record); self.save(value)
        self._event("implementation.added", {
            "name": record["name"], "language": record["implementation_language"],
            "level": level, "report": record["conformance_report"]["sha256"],
        })

    def add_lab_report(self, *, organization: str, country: str, scope: str, report: str | Path) -> None:
        record = {
            "organization": _require_text(organization, "organization"),
            "country": _country(country),
            "scope": _require_text(scope, "scope"),
            "report": self._store_evidence(report, "独立機関試験報告"),
            "recorded_at": _utc_now(),
        }
        value = self.load(); value["independent_labs"].append(record); self.save(value)
        self._event("independent_lab.report_added", {"organization": record["organization"], "country": record["country"], "report": record["report"]["sha256"]})

    def add_market_evidence(self, *, kind: str, title: str, country: str, evidence: str | Path) -> None:
        allowed = {"survey", "case_study", "procurement", "education", "industry_letter", "usage_metrics", "research"}
        if kind not in allowed:
            raise StandardsError(f"kind は次のいずれかです: {', '.join(sorted(allowed))}")
        record = {
            "kind": kind,
            "title": _require_text(title, "title"),
            "country": _country(country),
            "evidence": self._store_evidence(evidence, "市場性証拠"),
            "recorded_at": _utc_now(),
        }
        value = self.load(); value["market_evidence"].append(record); self.save(value)
        self._event("market_evidence.added", {"kind": kind, "country": record["country"], "evidence": record["evidence"]["sha256"]})

    def _evidence_ok(self, evidence: dict[str, Any] | None) -> bool:
        if not evidence or not isinstance(evidence, dict):
            return False
        stored = evidence.get("stored")
        expected = evidence.get("sha256")
        if not isinstance(stored, str) or not isinstance(expected, str):
            return False
        try:
            path = (self.root / stored).resolve()
            path.relative_to(self.root)
        except (OSError, ValueError):
            return False
        return path.is_file() and _sha256_bytes(path.read_bytes()) == expected

    def verify_evidence(self) -> tuple[bool, list[str]]:
        value = self.load()
        checks: list[tuple[str, dict[str, Any] | None]] = []
        if value.get("proposer"):
            checks.append(("proposer", value["proposer"].get("evidence")))
        if value.get("project_leader"):
            checks.append(("project_leader", value["project_leader"].get("consent")))
        for key, evidence_key in (
            ("experts", "consent"), ("p_member_commitments", "evidence"),
            ("adoptions", "evidence"), ("implementations", "conformance_report"),
            ("independent_labs", "report"), ("market_evidence", "evidence"),
        ):
            for index, item in enumerate(value.get(key, []), 1):
                checks.append((f"{key}[{index}]", item.get(evidence_key)))
        errors = [label for label, evidence in checks if not self._evidence_ok(evidence)]
        return not errors, errors

    def verify_event_chain(self) -> tuple[bool, str]:
        previous = "0" * 64
        if not self.event_file.exists():
            return False, "events.jsonl がありません"
        for number, line in enumerate(self.event_file.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            event = json.loads(line)
            actual_hash = event.pop("hash", None)
            if event.get("previous") != previous:
                return False, f"イベント{number}のpreviousが一致しません"
            expected = _sha256_bytes(_canonical(event))
            if actual_hash != expected:
                return False, f"イベント{number}のハッシュが一致しません"
            previous = actual_hash
        return True, previous

    def status(self) -> dict[str, Any]:
        value = self.load()
        proposer = value["proposer"] if value.get("proposer") and self._evidence_ok(value["proposer"].get("evidence")) else None
        leader = value["project_leader"] if value.get("project_leader") and self._evidence_ok(value["project_leader"].get("consent")) else None
        experts = [item for item in value.get("experts", []) if self._evidence_ok(item.get("consent"))]
        commitments = [item for item in value.get("p_member_commitments", []) if self._evidence_ok(item.get("evidence"))]
        adoptions = [item for item in value.get("adoptions", []) if self._evidence_ok(item.get("evidence"))]
        implementations = [item for item in value.get("implementations", []) if self._evidence_ok(item.get("conformance_report"))]
        labs = [item for item in value.get("independent_labs", []) if self._evidence_ok(item.get("report"))]
        market = [item for item in value.get("market_evidence", []) if self._evidence_ok(item.get("evidence"))]

        proposer_name = proposer["name"] if proposer else None
        expert_countries = {item["country"] for item in experts}
        expert_orgs = {item["organization"] for item in experts}
        adoption_countries = {item["country"] for item in adoptions}
        adoption_orgs = {item["organization"] for item in adoptions}
        p_countries = {item["country"] for item in commitments}
        market_countries = {item["country"] for item in market}
        independent_labs = [
            item for item in labs
            if proposer_name is None or item["organization"].casefold() != proposer_name.casefold()
        ]
        second_impl = [
            item for item in implementations
            if item["name"] != "saga-python"
            and item.get("independent_from") == "saga-python"
            and item.get("conformance_level", "experimental") in {"core", "full"}
        ]
        chain_ok, chain_detail = self.verify_event_chain()
        evidence_ok, evidence_errors = self.verify_evidence()
        criteria = {
            "eligible_proposer": proposer is not None,
            "project_leader_with_consent": leader is not None,
            "international_expert_team": len(experts) >= 5 and len(expert_countries) >= 3 and len(expert_orgs) >= 3,
            "five_p_member_commitments": len(p_countries) >= 5,
            "multi_country_adoption": len(adoption_countries) >= 3 and len(adoption_orgs) >= 3,
            "independent_second_implementation": bool(second_impl),
            "independent_conformance_lab": bool(independent_labs),
            "market_relevance_evidence": len(market) >= 3 and len(market_countries) >= 2,
            "tamper_evident_record": chain_ok and evidence_ok,
        }
        return {
            "project": value["project"],
            "criteria": criteria,
            "ready_for_np_submission": all(criteria.values()),
            "counts": {
                "experts": len(experts),
                "expert_countries": len(expert_countries),
                "expert_organizations": len(expert_orgs),
                "p_member_commitments": len(p_countries),
                "adoption_countries": len(adoption_countries),
                "adoption_organizations": len(adoption_orgs),
                "implementations": len(implementations),
                "qualifying_second_implementations": len(second_impl),
                "independent_labs": len(independent_labs),
                "market_evidence": len(market),
                "market_countries": len(market_countries),
            },
            "event_chain": {"valid": chain_ok, "head": chain_detail},
            "evidence": {"valid": evidence_ok, "invalid_records": evidence_errors},
            "note": "trueは証拠ファイルが登録され、現在のハッシュと整合したことを示します。ISO/IECまたは各National Bodyによる受理・承認を意味しません。",
        }

