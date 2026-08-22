from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from saga.checker import BUILTINS
from saga.stdlib import MODULES
from saga.tokens import KEYWORDS


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(root: Path, version: str) -> dict:
    return {
        "schema": 1,
        "language": "Saga",
        "version": version,
        "grammar_sha256": digest(root / "spec" / ("saga-1.0.ebnf" if version in {"0.14.0", "0.15.0", "0.17.0", "0.18.0", "0.19.0", "0.20.0", "0.22.0", "0.23.0", "0.26.2", "0.29.0", "0.30.0", "0.31.0", "0.32.0", "0.33.0", "0.34.0", "0.36.0", "0.37.0", "0.38.0", "0.42.0", "0.43.0", "0.44.0", "0.45.0", "0.46.0", "0.47.0", "0.49.0", "0.50.0"} else "saga-0.9.ebnf")),
        "keywords": sorted(KEYWORDS),
        "builtins": sorted(BUILTINS),
        "modules": {name: sorted(module.functions) for name, module in sorted(MODULES.items())},
        "semantic_changes": ([
            "bilingual_structured_diagnostics",
            "detailed_diagnostic_ids",
            "sarif_diagnostic_output",
            "locale_independent_conformance",
            "invalid_utf8_lexical_diagnostic",
            "unicode_project_names",
            "project_name_no_fixed_length_ceiling",
            "diagnostic_lsp_bridge",
        ] if version == "0.9.0" else ([
            "task_global_object_snapshot_fix",
            "private_display_redaction",
            "ascii_numeric_literal_profile",
            "websocket_capability_redirect_hardening",
            "canonical_stored_package_members",
            "explicit_conformance_diagnostic_ids",
            "go_standard_core_second_implementation",
            "isolated_python_plugin_host",
            "linux_namespace_plugin_sandbox",
            "strict_sandbox_fail_closed",
            "prose_independent_diagnostic_identity",
            "regex_hosted_module",
            "system_hosted_module",
            "cross_implementation_canonical_packaging",
        ] if version == "0.10.0" else ([
            "hosted_api_exhaustive_validation",
            "plugin_temporal_option_roundtrip",
            "external_value_boundary_hardening",
            "docdb_snapshot_semantics",
            "native_resource_cleanup_hardening",
            "cross_impl_set_format_conformance",
            "host_error_boundary_hardening",
            "native_resource_runtime_contracts",
            "documentation_implementation_alignment",
        ] if version == "0.10.1" else ([
            "lexical_closures",
            "registry_protocol",
            "ed25519_package_signing",
            "package_capability_metadata",
            "standard_native_runtime_aot",
            "wasi_runtime_aot",
            "scalar_direct_c_aot",
            "standard_core_mobile_runtime_source",
            "allowlisted_python_ecosystem_bridge",
            "static_capability_preview",
        ] if version == "0.12.0" else ([
            "language_edition_1_0_rc1",
            "result_type",
            "enum_record_match_exhaustiveness",
            "interpolated_strings",
            "standard_test_declarations",
            "native_hosted_standard_library",
            "dependency_free_game_baseline",
            "native_registry_and_publisher_trust_store",
            "direct_scalar_wasm_backend",
            "incremental_deterministic_build_cache",
            "post_typecheck_optimizer",
            "lightweight_cli_runtime_split",
            "in_memory_standalone_bundle_execution",
            "fixed_point_self_host_preserved",
        ] if version == "0.14.0" else ([
            "native_game_profile_1_0_rc1",
            "rgba8_framebuffer_and_image_textures",
            "sprite_camera_tilemap_particles_physics",
            "desktop_window_input_audio_gamepad",
            "gpu_renderer_and_programmable_shader_backend",
            "native_standardization_evidence_registry",
        ] if version in {"0.15.0", "0.17.0", "0.18.0", "0.19.0", "0.20.0", "0.22.0", "0.23.0", "0.26.2", "0.29.0", "0.30.0", "0.31.0", "0.32.0", "0.33.0", "0.34.0", "0.36.0", "0.37.0", "0.38.0", "0.42.0", "0.43.0", "0.44.0", "0.45.0", "0.46.0", "0.47.0", "0.49.0", "0.50.0"} else [])))))),
    }


def main() -> int:
    ap=argparse.ArgumentParser();ap.add_argument('--version',required=True);ap.add_argument('--output',required=True)
    args=ap.parse_args();root=ROOT
    out=root/args.output;out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(snapshot(root,args.version),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(out)
    return 0
if __name__=='__main__':raise SystemExit(main())
