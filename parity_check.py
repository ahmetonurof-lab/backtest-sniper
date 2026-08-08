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
  3. risk_manager.py kopya sapmasi (canli BUG-25 fix'leri backtest'te yok).

Kullanim:
    python parity_check.py            # rapor
    python parity_check.py --check    # CI: exit 0=PASS, 1=FAIL

Cikis kodu: 0 = parite tamam (PASS), 1 = sapma var (FAIL).
"""

# ruff: noqa: E402
import argparse
import ast
import copy
import hashlib
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SNIPER_SRC = os.path.join(_HERE, "..", "sniper", "src")
_BT_SRC = os.path.join(_HERE, "src")
_SNIPER_TRAILING = os.path.join(_SNIPER_SRC, "trading", "trailing_manager.py")
_SNIPER_CONFIG = os.path.join(_SNIPER_SRC, "config.py")
_BT_ANALYZER = os.path.join(_BT_SRC, "analyzer_v5.py")
_SNIPER_RISK = os.path.join(_SNIPER_SRC, "risk_manager.py")
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

    Bilinen mevcut degerler:
      canli config.py: TRAIL_MODE=os.environ.get(...,'activation'),
                       CONT_BUFFER_MULT=env('SNIPER_CONT_BUFFER_MULT','2.0'),
                       TRAIL_ACTIVATION_R_MULT=env('SNIPER_TRAIL_ACTIVATION_R_MULT','1.5'),
                       ATR_TRAIL_MULT=env('SNIPER_ATR_TRAIL_MULT','0.10'),
                       ATR_TRAIL_MULT_CONTINUATION=env('SNIPER_ATR_TRAIL_MULT_CONT','0.50'),
                       CONTINUATION_CONFIRM_BARS=env('SNIPER_CONT_CONFIRM_BARS','2'),
                       TRAIL_MIN_MOVE_MULT=0.2
      backtest analyzer_v5.py: TRAIL_MODE='retrace' (sabit, main() override),
                       CONT_BUFFER_MULT=getattr(cfg,'ATR_TRAIL_MULT_CONTINUATION',0.1)
                                       -> YANLIS: canli CONT_BUFFER_MULT=2.0 ayri anahtar.
                       TRAIL_ACTIVATION_R_MULT=1.0 (sabit, main() override 1.5)
    """
    problems = []
    live = _extract_config(_SNIPER_CONFIG, _CONFIG_KEYS)
    bt_src = open(_BT_ANALYZER, "r", encoding="utf-8").read()

    for key in _CONFIG_KEYS:
        if key not in live:
            problems.append(f"[CONFIG] canli config.py'de '{key}' tanimi yok")
            continue

    # CONT_BUFFER_MULT kopya-kaynak hatasi (en kritik): backtest, canlinin
    # CONT_BUFFER_MULT anahtarini DEGIL ATR_TRAIL_MULT_CONTINUATION'i okuyor.
    bt_cont = re.search(
        r"CONT_BUFFER_MULT\s*=\s*getattr\(\s*cfg,\s*[\"']([^\"']+)[\"']", bt_src
    )
    if bt_cont and bt_cont.group(1) != "CONT_BUFFER_MULT":
        problems.append(
            f"[CONFIG] KRITIK: backtest CONT_BUFFER_MULT, canli '{bt_cont.group(1)}' anahtarindan "
            f"okuyor. Canli CONT_BUFFER_MULT=2.0 (ATR-chase fallback K), "
            f"ATR_TRAIL_MULT_CONTINUATION=0.50 (continuation tamponu) AYRI anahtarlar. "
            f"Backtest getattr ile yanlis anahtara baglanmis — main()'deki K=2.0 override'i gizliyor."
        )

    # TRAIL_ACTIVATION_R_MULT sabit-1.0 vs canli 1.5
    bt_r = re.search(r"TRAIL_ACTIVATION_R_MULT\s*=\s*([\d.]+)", bt_src)
    live_r = re.search(r"\"1.5\"", live.get("TRAIL_ACTIVATION_R_MULT", ""))
    if bt_r and live_r:
        if bt_r.group(1) != "1.5":
            problems.append(
                f"[CONFIG] backtest TRAIL_ACTIVATION_R_MULT={bt_r.group(1)} sabit; "
                f"canli default 1.5. Modul import eden kod 1.0 ile calisir (main/worker override'i gizler)."
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
    if "activation" not in live_val:
        problems.append(
            f"[TRAIL_MODE] canli config default '{live_val}' — 'activation' bekleniyor"
        )
    if bt_default and bt_default != "activation":
        problems.append(
            f"[TRAIL_MODE] backtest modul sabiti TRAIL_MODE='{bt_default}' — canli default 'activation'. "
            f"main()/worker override'i dısındaki import kullanimlari {bt_default} ile calisir (sessiz sapma)."
        )
    return problems


def check_risk_manager() -> list[str]:
    problems = []
    if not (os.path.isfile(_SNIPER_RISK) and os.path.isfile(_BT_RISK)):
        return problems
    h1 = hashlib.md5(open(_SNIPER_RISK, "rb").read()).hexdigest()
    h2 = hashlib.md5(open(_BT_RISK, "rb").read()).hexdigest()
    if h1 != h2:
        n1 = sum(1 for _ in open(_SNIPER_RISK, "rb"))
        n2 = sum(1 for _ in open(_BT_RISK, "rb"))
        problems.append(
            f"[RISK_MANAGER] SAPMA: canli risk_manager.py ({n1} satir) != backtest kopyasi ({n2} satir). "
            f"Canli BUG-25 fix'leri (initial_equity fallback, DD=100 guvenli taraf) backtest'te yok. "
            f"Backtest kopyasi import edilmiyor (olu) — silinmeli veya senkronlanmali."
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
