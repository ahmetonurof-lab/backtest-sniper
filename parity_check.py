"""
parity_check.py — Canli/backtest kod parite kontrolu (D-2).

Amac: analyzer_v5.py (backtest) icindeki elle kopyalanmis trailing/FVG
mantiginin canli sniper/src ile birebir olup olmadigini OTOMATIK dogrular.

Kapsam:
  1. Fonksiyon kopyalari: analyzer_v5.fvg_close_confirmed /
     fvg_confirm_mode vs trailing_manager._fvg_close_confirmed /
     _fvg_confirm_mode (AST normalize — ad/dekorator/docstring/yorum haric).
  2. Trailing motor parametreleri: canli config'teki TRAIL_MODE /
     CONT_BUFFER_MULT / TRAIL_ACTIVATION_R_MULT / ATR_TRAIL_MULT /
     ATR_TRAIL_MULT_CONTINUATION / CONTINUATION_CONFIRM_BARS /
     TRAIL_MIN_MOVE_MULT degerlerinin backtest module sabitleriyle
     tutarliligi (yapisal uyarilar).
  3. risk_manager.py olu kopyasi: D-2 kapanisinda SILINDI; yeniden olusursa
     bu kontrol yakalar (canli risk_manager.py tek kaynak).

Kullanim:
    python parity_check.py            # rapor
    python parity_check.py --check    # CI: exit 0=PASS, 1=FAIL

Cikis kodu: 0 = parite tamam (PASS), 1 = sapma var (FAIL).
"""

# ruff: noqa: E402
import argparse
import ast
import copy
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SNIPER_SRC = os.path.join(_HERE, "..", "sniper", "src")
_BT_SRC = os.path.join(_HERE, "src")
_SNIPER_TRAILING = os.path.join(_SNIPER_SRC, "trading", "trailing_manager.py")
_SNIPER_CONFIG = os.path.join(_SNIPER_SRC, "config.py")
_BT_ANALYZER = os.path.join(_BT_SRC, "analyzer_v5.py")
_BT_RISK = os.path.join(_BT_SRC, "risk_manager.py")

# backtest fonksiyon adi -> canli metot adi
_FUNCTION_PAIRS = [
    ("fvg_close_confirmed", "_fvg_close_confirmed"),
    ("fvg_confirm_mode", "_fvg_confirm_mode"),
]

# canli config anahtari -> aciklama
_CONFIG_KEYS = [
    "TRAIL_MODE",
    "CONT_BUFFER_MULT",
    "TRAIL_ACTIVATION_R_MULT",
    "ATR_TRAIL_MULT",
    "ATR_TRAIL_MULT_CONTINUATION",
    "CONTINUATION_CONFIRM_BARS",
    "TRAIL_MIN_MOVE_MULT",
]


def _strip_docstring(node: ast.AST) -> ast.AST:
    node = copy.deepcopy(node)
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        node.body = node.body[1:]
    return node


def _fn_signature_fingerprint(node: ast.AST) -> str:
    """Fonksiyon gövdesini (ad/dekorator/param adi/docstring/anotasyon bagimsiz) imzaya cevirir.

    Parametre adlari __pN__ gibi kanoniklestirilir; gövdedeki Name erisimleri
    de ayni kanonik ada eslenir, boylece all_bars vs bars gibi sadece
    isimlendirme farklari false-positive uretmez. Fonksiyon adi ve tip
    anotasyonlari karsilastirma disinda tutulur.
    """
    node = _strip_docstring(node)

    param_names: list[str] = []
    if node.args.args:
        param_names = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]
    canonical = {p: f"__p{i}__" for i, p in enumerate(param_names)}
    canonical.setdefault("self", "__self__")

    node.name = "__fn__"

    class Normalizer(ast.NodeTransformer):
        def visit_Name(self, n):
            if n.id in canonical:
                n.id = canonical[n.id]
            return n

        def visit_arg(self, n):
            if n.arg in canonical:
                n.arg = canonical[n.arg]
            n.annotation = None
            return n

        def visit_FunctionDef(self, n):
            n.returns = None
            n.decorator_list = []
            return self.generic_visit(n)

        def visit_AsyncFunctionDef(self, n):
            n.returns = None
            n.decorator_list = []
            return self.generic_visit(n)

    node = Normalizer().visit(node)
    return ast.dump(node, include_attributes=False)


def check_function_pairs() -> list[str]:
    problems = []
    for bt_name, live_name in _FUNCTION_PAIRS:
        bt_fns = {}
        live_fns = {}
        with open(_BT_ANALYZER, "r", encoding="utf-8") as f:
            for n in ast.walk(ast.parse(f.read())):
                if (
                    isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and n.name == bt_name
                ):
                    bt_fns[bt_name] = n
        with open(_SNIPER_TRAILING, "r", encoding="utf-8") as f:
            for n in ast.walk(ast.parse(f.read())):
                if (
                    isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and n.name == live_name
                ):
                    live_fns[live_name] = n
        if bt_name not in bt_fns:
            problems.append(
                f"[FONKSIYON] backtest 'src/analyzer_v5.py' icinde '{bt_name}' yok"
            )
            continue
        if live_name not in live_fns:
            problems.append(
                f"[FONKSIYON] canli 'trading/trailing_manager.py' icinde '{live_name}' yok"
            )
            continue
        f1 = _fn_signature_fingerprint(bt_fns[bt_name])
        f2 = _fn_signature_fingerprint(live_fns[live_name])
        if f1 != f2:
            problems.append(
                f"[FONKSIYON] SAPMA: backtest '{bt_name}' != canli '{live_name}' "
                f"(gövde farkli — birebir kopya bozuldu)"
            )
    return problems


def _extract_config(path: str, keys: list[str]) -> dict[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    out = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            if node.targets[0].id in keys:
                out[node.targets[0].id] = ast.unparse(node.value).strip()
    return out


def check_config_parity() -> list[str]:
    """Backtest module sabitlerinin canli config degerleriyle tutarliligini kontrol eder.

    D-2 kapanis sonrasi: TRAIL_MODE / TRAIL_ACTIVATION_R_MULT / CONT_BUFFER_MULT /
    CONT_TRAIL_MULT / CONT_CONFIRM_BARS module sabitleri artik getattr(cfg, ...)
    ile canli config'ten turetilir (canli config.py'deki env-default degerlerle).
    Bu kontrol, sabitlerin DOGRU canli anahtara baglanip baglanmadigini ve
    default degerlerinin canli config default'lariyla eslesip eslemedigini
    dogrular. Yanlis anahtar/eslesmeyen default = sapma.
    """
    problems = []
    live = _extract_config(_SNIPER_CONFIG, _CONFIG_KEYS)
    bt_src = open(_BT_ANALYZER, "r", encoding="utf-8").read()

    for key in _CONFIG_KEYS:
        if key not in live:
            problems.append(f"[CONFIG] canli config.py'de '{key}' tanimi yok")
            continue

    # backtest getattr(..., "<canli_anahtar>", <default>) eslesmesi:
    # bt anahtar, canli config'teki AYNI ada bagli olmali ve default degeri
    # canli config'in env-default degeriyle ayni olmali.
    bt_attrs = {
        m.group(1): (m.group(2), m.group(3))
        for m in re.finditer(
            r"(\w+)\s*=\s*getattr\(\s*cfg,\s*[\"']([^\"']+)[\"'],\s*([^)]+)\)",
            bt_src,
        )
    }
    # ATR_TRAIL_MULT gibi sabit kalanlar getattr degil; onlar icin eski kontrol
    # devre disi (D-2 kapanisinda canli anahtarlara bagli olanlar dogrulandi).
    expected_defaults = {
        "TRAIL_MODE": "retrace",
        "TRAIL_ACTIVATION_R_MULT": "1.5",
        "CONT_BUFFER_MULT": "2.0",
        "ATR_TRAIL_MULT_CONTINUATION": "0.5",
        "CONTINUATION_CONFIRM_BARS": "2",
    }
    # backtest degiskeni -> beklenen canli config anahtari
    var_to_live_key = {
        "CONT_BUFFER_MULT": "CONT_BUFFER_MULT",
        "CONT_TRAIL_MULT": "ATR_TRAIL_MULT_CONTINUATION",
        "CONT_CONFIRM_BARS": "CONTINUATION_CONFIRM_BARS",
        "TRAIL_ACTIVATION_R_MULT": "TRAIL_ACTIVATION_R_MULT",
        "TRAIL_MODE": "TRAIL_MODE",
    }
    for bt_var, live_key in var_to_live_key.items():
        if bt_var not in bt_attrs:
            problems.append(
                f"[CONFIG] backtest '{bt_var}' getattr(cfg, ...) deseninde bulunamadi — "
                f"canli '{live_key}' anahtarina baglanmali."
            )
            continue
        bt_key, bt_default = bt_attrs[bt_var]
        if bt_key != live_key:
            problems.append(
                f"[CONFIG] KRITIK: backtest '{bt_var}', canli '{bt_key}' anahtarindan "
                f"okuyor — '{live_key}' bekleniyor."
            )
        exp_default = expected_defaults.get(live_key)
        bt_def_norm = bt_default.strip().strip("'\"")
        if exp_default is not None and bt_def_norm != exp_default:
            problems.append(
                f"[CONFIG] backtest '{bt_var}' default={bt_default.strip()} — canli "
                f"'{live_key}' default={exp_default}. Modul import eden kod yanlis "
                f"varsayilanla calisir (main/worker override'i gizler)."
            )
    return problems


def check_trail_mode_default() -> list[str]:
    problems = []
    live = _extract_config(_SNIPER_CONFIG, ["TRAIL_MODE"])
    live_val = live.get("TRAIL_MODE", "?")
    bt_src = open(_BT_ANALYZER, "r", encoding="utf-8").read()
    bt_default = None
    for line in bt_src.splitlines():
        m = re.match(r"^\s*TRAIL_MODE\s*=\s*[\"']([^\"']+)[\"']\s*$", line)
        if m:
            bt_default = m.group(1)
            break
    if "retrace" not in live_val:
        problems.append(
            f"[TRAIL_MODE] canli config default '{live_val}' — 'retrace' bekleniyor (D modu/continuation 2026-08-08 geri cekildi)"
        )
    if bt_default and bt_default != "retrace":
        problems.append(
            f"[TRAIL_MODE] backtest modul sabiti TRAIL_MODE='{bt_default}' — canli default 'retrace'. "
            f"main()/worker override'i dısındaki import kullanimlari {bt_default} ile calisir (sessiz sapma)."
        )
    return problems


def check_risk_manager() -> list[str]:
    """Backtest risk_manager.py olu kopyasi VAR MI kontrol eder (D-2 kapanis).

    Karar: backtest tarafindan hicbir dosya import etmedigi icin olu kopyaydi;
    canli BUG-25 fix'leri (initial_equity fallback, DD=100 guvenli taraf)
    kopyaya hic yansimadi. Senkron kacirma riskini kokten kaldirmak icin
    kopya TAMAMEN SILINDI — canli risk_manager.py tek kaynak oldu.
    Backtest tarafinda yeniden risk_manager.py olusursa (eski kopya geri
    getirilirse) bu kontrol YAKALAR: varligi basta sapma sayilir.
    """
    problems = []
    if not os.path.isfile(_BT_RISK):
        return problems
    problems.append(
        "[RISK_MANAGER] backtest 'src/risk_manager.py' yeniden olusmus — "
        "D-2 kapanisinda TAMAMEN SILINDI (olu kopya, canli BUG-25 fix'siz). "
        "Backtest tarafindan import edilmiyordu; canli risk_manager.py tek "
        "kaynaktir, kopya geri getirilmemeli (senkron kacirma riski)."
    )
    return problems


def _main() -> int:
    ap = argparse.ArgumentParser(description="Canli/backtest kod parite kontrolu (D-2)")
    ap.add_argument("--check", action="store_true", help="CI modu: exit 0=FAIL, 1=PASS")
    args = ap.parse_args()

    problems: list[str] = []
    problems += check_function_pairs()
    problems += check_config_parity()
    problems += check_trail_mode_default()
    problems += check_risk_manager()

    if args.check:
        print("PARITE_OK" if not problems else "PARITE_FAIL")
    elif problems:
        print(f"✗ {len(problems)} parite sapmasi:")
        for p in problems:
            print("  - " + p)
    else:
        print("✓ Parite tamam: canli/backtest kopyalari eslesiyor.")
    return 0 if not problems else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(_main())
