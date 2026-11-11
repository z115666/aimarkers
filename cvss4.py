# aimarkers: ignore-file
"""
CVSS v4.0: cálculo de la puntuación / score calculation.

Traducción a Python del algoritmo de referencia de FIRST (calculadora oficial
https://github.com/FIRSTdotorg/cvss-v4-calculator, commit c5b0d40). Las tablas
de MacroVectores, distancias máximas y vectores de mayor severidad son las de la
especificación (https://www.first.org/cvss/v4.0/specification-document).

Copyright (c) 2023 FIRST.ORG, Inc., Red Hat, and contributors
Python translation: Copyright (c) 2026 Alberto

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from __future__ import annotations

import math
import re

ORDEN = ["AV", "AC", "AT", "PR", "UI", "VC", "VI", "VA", "SC", "SI", "SA", "E", "CR", "IR", "AR",
         "MAV", "MAC", "MAT", "MPR", "MUI", "MVC", "MVI", "MVA", "MSC", "MSI", "MSA",
         "S", "AU", "R", "V", "RE", "U"]
VALORES = {
    "AV": "NALP", "AC": "LH", "AT": "NP", "PR": "NLH", "UI": "NPA",
    "VC": "HLN", "VI": "HLN", "VA": "HLN", "SC": "HLN", "SI": "HLN", "SA": "HLN",
    "E": "XAPU", "CR": "XHML", "IR": "XHML", "AR": "XHML",
    "MAV": "XNALP", "MAC": "XLH", "MAT": "XNP", "MPR": "XNLH", "MUI": "XNPA",
    "MVC": "XHLN", "MVI": "XHLN", "MVA": "XHLN", "MSC": "XHLN", "MSI": "XSHLN", "MSA": "XSHLN",
    "S": "XNP", "AU": "XNY", "R": "XAUI", "V": "XDC", "RE": "XLMH", "U": "X",
}
OBLIGATORIAS = ORDEN[:11]

LOOKUP = {
    "000000": 10, "000001": 9.9, "000010": 9.8, "000011": 9.5, "000020": 9.5, "000021": 9.2, "000100": 10, "000101": 9.6,
    "000110": 9.3, "000111": 8.7, "000120": 9.1, "000121": 8.1, "000200": 9.3, "000201": 9, "000210": 8.9, "000211": 8,
    "000220": 8.1, "000221": 6.8, "001000": 9.8, "001001": 9.5, "001010": 9.5, "001011": 9.2, "001020": 9, "001021": 8.4,
    "001100": 9.3, "001101": 9.2, "001110": 8.9, "001111": 8.1, "001120": 8.1, "001121": 6.5, "001200": 8.8, "001201": 8,
    "001210": 7.8, "001211": 7, "001220": 6.9, "001221": 4.8, "002001": 9.2, "002011": 8.2, "002021": 7.2, "002101": 7.9,
    "002111": 6.9, "002121": 5, "002201": 6.9, "002211": 5.5, "002221": 2.7, "010000": 9.9, "010001": 9.7, "010010": 9.5,
    "010011": 9.2, "010020": 9.2, "010021": 8.5, "010100": 9.5, "010101": 9.1, "010110": 9, "010111": 8.3, "010120": 8.4,
    "010121": 7.1, "010200": 9.2, "010201": 8.1, "010210": 8.2, "010211": 7.1, "010220": 7.2, "010221": 5.3, "011000": 9.5,
    "011001": 9.3, "011010": 9.2, "011011": 8.5, "011020": 8.5, "011021": 7.3, "011100": 9.2, "011101": 8.2, "011110": 8,
    "011111": 7.2, "011120": 7, "011121": 5.9, "011200": 8.4, "011201": 7, "011210": 7.1, "011211": 5.2, "011220": 5,
    "011221": 3, "012001": 8.6, "012011": 7.5, "012021": 5.2, "012101": 7.1, "012111": 5.2, "012121": 2.9, "012201": 6.3,
    "012211": 2.9, "012221": 1.7, "100000": 9.8, "100001": 9.5, "100010": 9.4, "100011": 8.7, "100020": 9.1, "100021": 8.1,
    "100100": 9.4, "100101": 8.9, "100110": 8.6, "100111": 7.4, "100120": 7.7, "100121": 6.4, "100200": 8.7, "100201": 7.5,
    "100210": 7.4, "100211": 6.3, "100220": 6.3, "100221": 4.9, "101000": 9.4, "101001": 8.9, "101010": 8.8, "101011": 7.7,
    "101020": 7.6, "101021": 6.7, "101100": 8.6, "101101": 7.6, "101110": 7.4, "101111": 5.8, "101120": 5.9, "101121": 5,
    "101200": 7.2, "101201": 5.7, "101210": 5.7, "101211": 5.2, "101220": 5.2, "101221": 2.5, "102001": 8.3, "102011": 7,
    "102021": 5.4, "102101": 6.5, "102111": 5.8, "102121": 2.6, "102201": 5.3, "102211": 2.1, "102221": 1.3, "110000": 9.5,
    "110001": 9, "110010": 8.8, "110011": 7.6, "110020": 7.6, "110021": 7, "110100": 9, "110101": 7.7, "110110": 7.5,
    "110111": 6.2, "110120": 6.1, "110121": 5.3, "110200": 7.7, "110201": 6.6, "110210": 6.8, "110211": 5.9, "110220": 5.2,
    "110221": 3, "111000": 8.9, "111001": 7.8, "111010": 7.6, "111011": 6.7, "111020": 6.2, "111021": 5.8, "111100": 7.4,
    "111101": 5.9, "111110": 5.7, "111111": 5.7, "111120": 4.7, "111121": 2.3, "111200": 6.1, "111201": 5.2, "111210": 5.7,
    "111211": 2.9, "111220": 2.4, "111221": 1.6, "112001": 7.1, "112011": 5.9, "112021": 3, "112101": 5.8, "112111": 2.6,
    "112121": 1.5, "112201": 2.3, "112211": 1.3, "112221": 0.6, "200000": 9.3, "200001": 8.7, "200010": 8.6, "200011": 7.2,
    "200020": 7.5, "200021": 5.8, "200100": 8.6, "200101": 7.4, "200110": 7.4, "200111": 6.1, "200120": 5.6, "200121": 3.4,
    "200200": 7, "200201": 5.4, "200210": 5.2, "200211": 4, "200220": 4, "200221": 2.2, "201000": 8.5, "201001": 7.5,
    "201010": 7.4, "201011": 5.5, "201020": 6.2, "201021": 5.1, "201100": 7.2, "201101": 5.7, "201110": 5.5, "201111": 4.1,
    "201120": 4.6, "201121": 1.9, "201200": 5.3, "201201": 3.6, "201210": 3.4, "201211": 1.9, "201220": 1.9, "201221": 0.8,
    "202001": 6.4, "202011": 5.1, "202021": 2, "202101": 4.7, "202111": 2.1, "202121": 1.1, "202201": 2.4, "202211": 0.9,
    "202221": 0.4, "210000": 8.8, "210001": 7.5, "210010": 7.3, "210011": 5.3, "210020": 6, "210021": 5, "210100": 7.3,
    "210101": 5.5, "210110": 5.9, "210111": 4, "210120": 4.1, "210121": 2, "210200": 5.4, "210201": 4.3, "210210": 4.5,
    "210211": 2.2, "210220": 2, "210221": 1.1, "211000": 7.5, "211001": 5.5, "211010": 5.8, "211011": 4.5, "211020": 4,
    "211021": 2.1, "211100": 6.1, "211101": 5.1, "211110": 4.8, "211111": 1.8, "211120": 2, "211121": 0.9, "211200": 4.6,
    "211201": 1.8, "211210": 1.7, "211211": 0.7, "211220": 0.8, "211221": 0.2, "212001": 5.3, "212011": 2.4, "212021": 1.4,
    "212101": 2.4, "212111": 1.2, "212121": 0.5, "212201": 1, "212211": 0.3, "212221": 0.1,
}

MAX_COMPUESTOS = {
    "eq1": {0: ["AV:N/PR:N/UI:N/"], 1: ["AV:A/PR:N/UI:N/", "AV:N/PR:L/UI:N/", "AV:N/PR:N/UI:P/"],
            2: ["AV:P/PR:N/UI:N/", "AV:A/PR:L/UI:P/"]},
    "eq2": {0: ["AC:L/AT:N/"], 1: ["AC:H/AT:N/", "AC:L/AT:P/"]},
    "eq3": {
        0: {"0": ["VC:H/VI:H/VA:H/CR:H/IR:H/AR:H/"],
            "1": ["VC:H/VI:H/VA:L/CR:M/IR:M/AR:H/", "VC:H/VI:H/VA:H/CR:M/IR:M/AR:M/"]},
        1: {"0": ["VC:L/VI:H/VA:H/CR:H/IR:H/AR:H/", "VC:H/VI:L/VA:H/CR:H/IR:H/AR:H/"],
            "1": ["VC:L/VI:H/VA:L/CR:H/IR:M/AR:H/", "VC:L/VI:H/VA:H/CR:H/IR:M/AR:M/",
                  "VC:H/VI:L/VA:H/CR:M/IR:H/AR:M/", "VC:H/VI:L/VA:L/CR:M/IR:H/AR:H/",
                  "VC:L/VI:L/VA:H/CR:H/IR:H/AR:M/"]},
        2: {"1": ["VC:L/VI:L/VA:L/CR:H/IR:H/AR:H/"]},
    },
    "eq4": {0: ["SC:H/SI:S/SA:S/"], 1: ["SC:H/SI:H/SA:H/"], 2: ["SC:L/SI:L/SA:L/"]},
    "eq5": {0: ["E:A/"], 1: ["E:P/"], 2: ["E:U/"]},
}
MAX_SEVERIDAD = {
    "eq1": {0: 1, 1: 4, 2: 5}, "eq2": {0: 1, 1: 2},
    "eq3eq6": {0: {0: 7, 1: 6}, 1: {0: 8, 1: 8}, 2: {1: 10}}, "eq4": {0: 6, 1: 5, 2: 4}, "eq5": {0: 1, 1: 1, 2: 1},
}
NIVELES = {
    "AV": {"N": 0.0, "A": 0.1, "L": 0.2, "P": 0.3}, "PR": {"N": 0.0, "L": 0.1, "H": 0.2},
    "UI": {"N": 0.0, "P": 0.1, "A": 0.2}, "AC": {"L": 0.0, "H": 0.1}, "AT": {"N": 0.0, "P": 0.1},
    "VC": {"H": 0.0, "L": 0.1, "N": 0.2}, "VI": {"H": 0.0, "L": 0.1, "N": 0.2}, "VA": {"H": 0.0, "L": 0.1, "N": 0.2},
    "SC": {"H": 0.1, "L": 0.2, "N": 0.3}, "SI": {"S": 0.0, "H": 0.1, "L": 0.2, "N": 0.3},
    "SA": {"S": 0.0, "H": 0.1, "L": 0.2, "N": 0.3},
    "CR": {"H": 0.0, "M": 0.1, "L": 0.2}, "IR": {"H": 0.0, "M": 0.1, "L": 0.2}, "AR": {"H": 0.0, "M": 0.1, "L": 0.2},
}
RE_VECTOR = re.compile(r"^CVSS:4\.0(/[A-Z]{1,3}:[A-Z])+$")


class VectorInvalido(ValueError):
    pass


def parsear(vector: str) -> dict[str, str]:
    """Convierte un vector CVSS:4.0/... en un diccionario validado."""
    if not RE_VECTOR.match(vector):
        raise VectorInvalido(vector)
    metricas: dict[str, str] = {}
    for parte in vector.split("/")[1:]:
        clave, valor = parte.split(":")
        if clave not in VALORES or valor not in VALORES[clave] or clave in metricas:
            raise VectorInvalido(vector)
        metricas[clave] = valor
    if any(c not in metricas for c in OBLIGATORIAS):
        raise VectorInvalido(vector)
    for clave in VALORES:
        metricas.setdefault(clave, "X")
    return metricas


def _m(sel: dict[str, str], metrica: str) -> str:
    valor = sel.get(metrica, "X")
    if metrica == "E" and valor == "X":
        return "A"
    if metrica in ("CR", "IR", "AR") and valor == "X":
        return "H"
    modificada = sel.get("M" + metrica)
    if modificada is not None and modificada != "X":
        return modificada
    return valor


def macrovector(sel: dict[str, str]) -> str:
    av, pr, ui = _m(sel, "AV"), _m(sel, "PR"), _m(sel, "UI")
    if av == "N" and pr == "N" and ui == "N":
        eq1 = 0
    elif (av == "N" or pr == "N" or ui == "N") and av != "P":
        eq1 = 1
    else:
        eq1 = 2
    eq2 = 0 if _m(sel, "AC") == "L" and _m(sel, "AT") == "N" else 1
    vc, vi, va = _m(sel, "VC"), _m(sel, "VI"), _m(sel, "VA")
    if vc == "H" and vi == "H":
        eq3 = 0
    elif vc == "H" or vi == "H" or va == "H":
        eq3 = 1
    else:
        eq3 = 2
    if _m(sel, "MSI") == "S" or _m(sel, "MSA") == "S":
        eq4 = 0
    elif _m(sel, "SC") == "H" or _m(sel, "SI") == "H" or _m(sel, "SA") == "H":
        eq4 = 1
    else:
        eq4 = 2
    eq5 = {"A": 0, "P": 1, "U": 2}[_m(sel, "E")]
    alta = ((_m(sel, "CR") == "H" and vc == "H") or (_m(sel, "IR") == "H" and vi == "H")
            or (_m(sel, "AR") == "H" and va == "H"))
    eq6 = 0 if alta else 1
    return f"{eq1}{eq2}{eq3}{eq4}{eq5}{eq6}"


def _valor_en(metrica: str, texto: str) -> str:
    resto = texto[texto.index(metrica) + len(metrica) + 1:]
    return resto.split("/", 1)[0]


def _redondear(valor: float) -> float:
    return math.floor(valor * 10 + 0.5) / 10  # como Math.round de JavaScript para valores positivos


def puntuacion(vector: str) -> float:
    """Puntuación CVSS v4.0 (0.0-10.0) de un vector, con el algoritmo de FIRST."""
    sel = parsear(vector)
    if all(_m(sel, x) == "N" for x in ("VC", "VI", "VA", "SC", "SI", "SA")):
        return 0.0
    mv = macrovector(sel)
    valor = LOOKUP[mv]
    eq1, eq2, eq3, eq4, eq5, eq6 = (int(c) for c in mv)

    def puntos(clave: str) -> float:
        return LOOKUP.get(clave, math.nan)

    siguiente_eq1 = puntos(f"{eq1 + 1}{eq2}{eq3}{eq4}{eq5}{eq6}")
    siguiente_eq2 = puntos(f"{eq1}{eq2 + 1}{eq3}{eq4}{eq5}{eq6}")
    if eq3 == 1 and eq6 == 1 or eq3 == 0 and eq6 == 1:
        siguiente_eq3eq6 = puntos(f"{eq1}{eq2}{eq3 + 1}{eq4}{eq5}{eq6}")
    elif eq3 == 1 and eq6 == 0:
        siguiente_eq3eq6 = puntos(f"{eq1}{eq2}{eq3}{eq4}{eq5}{eq6 + 1}")
    elif eq3 == 0 and eq6 == 0:
        izquierda = puntos(f"{eq1}{eq2}{eq3}{eq4}{eq5}{eq6 + 1}")
        derecha = puntos(f"{eq1}{eq2}{eq3 + 1}{eq4}{eq5}{eq6}")
        siguiente_eq3eq6 = izquierda if izquierda > derecha else derecha
    else:
        siguiente_eq3eq6 = puntos(f"{eq1}{eq2}{eq3 + 1}{eq4}{eq5}{eq6 + 1}")
    siguiente_eq4 = puntos(f"{eq1}{eq2}{eq3}{eq4 + 1}{eq5}{eq6}")
    siguiente_eq5 = puntos(f"{eq1}{eq2}{eq3}{eq4}{eq5 + 1}{eq6}")

    maximos = [a + b + c + d + e
               for a in MAX_COMPUESTOS["eq1"][eq1]
               for b in MAX_COMPUESTOS["eq2"][eq2]
               for c in MAX_COMPUESTOS["eq3"][eq3][str(eq6)]
               for d in MAX_COMPUESTOS["eq4"][eq4]
               for e in MAX_COMPUESTOS["eq5"][eq5]]
    distancias: dict[str, float] = {}
    for maximo in maximos:
        distancias = {x: NIVELES[x][_m(sel, x)] - NIVELES[x][_valor_en(x, maximo)] for x in NIVELES}
        if not any(d < 0 for d in distancias.values()):
            break

    d = distancias
    actual_eq1 = d["AV"] + d["PR"] + d["UI"]
    actual_eq2 = d["AC"] + d["AT"]
    actual_eq3eq6 = d["VC"] + d["VI"] + d["VA"] + d["CR"] + d["IR"] + d["AR"]
    actual_eq4 = d["SC"] + d["SI"] + d["SA"]
    paso = 0.1
    disponibles = [
        (valor - siguiente_eq1, actual_eq1, MAX_SEVERIDAD["eq1"][eq1] * paso),
        (valor - siguiente_eq2, actual_eq2, MAX_SEVERIDAD["eq2"][eq2] * paso),
        (valor - siguiente_eq3eq6, actual_eq3eq6, MAX_SEVERIDAD["eq3eq6"][eq3][eq6] * paso),
        (valor - siguiente_eq4, actual_eq4, MAX_SEVERIDAD["eq4"][eq4] * paso),
        (valor - siguiente_eq5, 0.0, 1.0),
    ]
    existentes = 0
    suma = 0.0
    for disponible, actual, maximo in disponibles:
        if not math.isnan(disponible):
            existentes += 1
            suma += disponible * (actual / maximo)
    media = suma / existentes if existentes else 0.0
    valor -= media
    return _redondear(min(10.0, max(0.0, valor)))


def severidad(valor: float | None) -> str:
    """Valoración cualitativa de FIRST: none, low, medium, high, critical."""
    if valor is None or valor == 0:
        return "none"
    if valor < 4.0:
        return "low"
    if valor < 7.0:
        return "medium"
    if valor < 9.0:
        return "high"
    return "critical"


def componer(base: str, **extra: str) -> str:
    """Añade métricas de amenaza o entorno a un vector base respetando el orden de la especificación."""
    metricas = {k: v for k, v in parsear(base).items() if v != "X"}
    metricas.update({k: v for k, v in extra.items() if v and v != "X"})
    return "CVSS:4.0/" + "/".join(f"{k}:{metricas[k]}" for k in ORDEN if k in metricas)
