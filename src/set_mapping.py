"""Set code mapping from PTCG Live codes to TCGDex API set IDs."""

SET_CODE_MAP: dict[str, str] = {
    # Scarlet & Violet Base
    "SVI": "sv01",
    "PAL": "sv02",
    "OBF": "sv03",
    "MEW": "sv03.5",
    "PAF": "sv04.5",
    "PRF": "sv04",
    "TEF": "sv05",
    "TWM": "sv06",
    "SFA": "sv06.5",
    "SCR": "sv07",
    "SSP": "sv08",
    "PRE": "sv08.5",
    "JTG": "sv09",
    "DRI": "sv10",
    # Promos & Special
    "SVP": "svp",
    "MEP": "mep",
    "SVE": "sve",
    # Mega Evolution (ACE SPEC era)
    "MEG": "me01",
    "MEG2": "me02",
    # Older sets
    "ASR": "swsh10",
    "LOR": "swsh11",
    "SIT": "swsh12",
    "CRZ": "swsh12.5",
    "PAR": "sv04",
}
