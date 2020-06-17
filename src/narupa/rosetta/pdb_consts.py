# Copyright (c) Tim Neary, University of Bristol. Github username: TENeary, contact: tn15550@bristol.ac.uk
# Licensed under the GPL. See License.txt in the project root for license information.

ATOM_IDS = { # Taken from narupa.mdanalysis.converter ELEMENT_INDEX but all string entries are fully captalised
    'H' : 1,
    'HE': 2,
    'LI': 3,
    'BE': 4,
    'B' : 5,
    'C' : 6,
    'N' : 7,
    'O' : 8,
    'F' : 9,
    'NE': 10,
    'NA': 11,
    'MG': 12,
    'AL': 13,
    'SI': 14,
    'P' : 15,
    'S' : 16,
    'CL': 17,
    'AR': 18,
    'K' : 19,
    'CA': 20,
    'SC': 21,
    'TI': 22,
    'V' : 23,
    'CR': 24,
    'MN': 25,
    'FE': 26,
    'CO': 27,
    'NI': 28,
    'CU': 29,
    'ZN': 30,
    'GA': 31,
    'GE': 32,
    'AS': 33,
    'SE': 34,
    'BR': 35,
    'KR': 36,
    'RB': 37,
    'SR': 38,
    'Y' : 39,
    'ZR': 40,
    'NB': 41,
    'MO': 42,
    'TC': 43,
    'RU': 44,
    'RH': 45,
    'PD': 46,
    'AG': 47,
    'CD': 48,
    'IN': 49,
    'SN': 50,
    'SB': 51,
    'TE': 52,
    'I' : 53,
    'XE': 54,
    'CS': 55,
    'BA': 56,
    'LA': 57,
    'CE': 58,
    'PR': 59,
    'ND': 60,
    'PM': 61,
    'SM': 62,
    'EE': 63,
    'GD': 64,
    'TB': 65,
    'DY': 66,
    'HO': 67,
    'ER': 68,
    'TU': 69,
    'YB': 70,
    'LU': 71,
    'HF': 72,
    'TA': 73,
    'W' : 74,
    'RE': 75,
    'OS': 76,
    'IR': 77,
    'PT': 78,
    'AU': 79,
    'HG': 80,
    'TL': 81,
    'PB': 82,
    'BI': 83,
    'PO': 84,
    'AT': 85,
    'RN': 86,
    'FR': 87,
    'RA': 88,
    'AC': 89,
    'TH': 90,
    'PA': 91,
    'U' : 92,
    'NP': 93,
    'PU': 94,
    'AM': 95,
    'CM': 96,
    'BK': 97,
    'CF': 98,
    'ES': 99,
    'FM': 100,
    'MD': 101,
    'NO': 102,
    'LR': 103,
    'RF': 104,
    'DB': 105,
    'SG': 106,
    'BH': 107,
    'HS': 108,
    'MT': 109,
    'DS': 110,
    'RG': 111,
    'CN': 112,
    'NH': 113,
    'FV': 114,
    'MS': 115,
    'LV': 116,
    'TS': 117,
    'OG': 118
}


RES3_INFO = { # Correspond to only 20 standard AAs
  # Contains: Number of atoms in residue, N-terminal linkage atom, C-terminal linkage atom
  "ALA" : ( 10, 0, 2 ),
  "CYS" : ( 10, 0, 2 ),
  "ASP" : ( 12, 0, 2 ),
  "GLU" : ( 15, 0, 2 ),
  "PHE" : ( 20, 0, 2 ),
  "GLY" : ( 7,  0, 2 ),
  "HIS" : ( 17, 0, 2 ),
  "ILE" : ( 19, 0, 2 ),
  "LYS" : ( 22, 0, 2 ),
  "LEU" : ( 19, 0, 2 ),
  "MET" : ( 17, 0, 2 ),
  "ASN" : ( 14, 0, 2 ),
  "PRO" : ( 14, 0, 2 ),
  "GLN" : ( 17, 0, 2 ),
  "ARG" : ( 24, 0, 2 ),
  "SER" : ( 11, 0, 2 ),
  "THR" : ( 14, 0, 2 ),
  "VAL" : ( 16, 0, 2 ),
  "TRP" : ( 24, 0, 2 ),
  "TYR" : ( 21, 0, 2 ),
}


RES_LINKAGES = { # Correspond to the 20 standard AAs
  # Contains the residue linkages based on atom number, 0 indexed.
  # This dict uses Rosetta numbering for atoms to maintain consistency.
  # This dict should not be used outside of Rosetta generated pdbs
  "ALA" : [[0, 5], [0, 1], [1, 6], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 7], [4, 8], [4, 9]],
  # CYS is mostly written without H on S unless explicitly stated, TODO account for CYS WITH H
  "CYS" : [[0, 6], [0, 1], [1, 7], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5], [4, 8], [4, 9]],
  "ASP" : [[0, 8], [0, 1], [1, 9], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5], [5, 6], [5, 7],
           [4, 10], [4, 11]],
  "GLU" : [[0, 9], [0, 1], [1, 10], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5], [5, 6], [6, 7], [6, 8],
           [4, 11], [4, 12], [5, 13], [5, 14]],
  "PHE" : [[0, 11], [0, 1], [1, 12], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5], # Arm Section + H's
           [5, 6], [5, 7], [6, 8], [7, 9], [8, 10], [9, 10], # Cyclic section
           [4, 13], [4, 14], [6, 15], [7, 16], [8, 17], [9, 18], [10, 19]],
  "GLY" : [[0, 4], [0, 1], [1, 5], [1, 2], [2, 3], [1, 5], [1, 6]], # BackboneLinkages
  # TODO have a way to get linkages for either His isomer
  "HIS" : [[0, 10], [0, 1], [1, 11], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5],  # Arm Section + H's
           [5, 6], [5, 7], [6, 8], [7, 9], [8, 9], # Cyclic section
           [4, 12], [4, 13], [7, 14], [8, 15], [9, 16]],
  "ILE" : [[0, 8], [0, 1], [1, 9], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5], [4, 6], [5, 7],
           [4, 10], [5, 11], [5, 12], [6, 13], [6, 14], [6, 15], [7, 16], [7, 17], [7, 18]],
  "LYS" : [[0, 9], [0, 1], [1, 10], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5], [5, 6], [6, 7], [7, 8],
           [4, 11], [4, 12], [5, 13], [5, 14], [6, 15], [6, 16], [7, 17], [7, 18], [8, 19], [8, 20], [8, 21]],
  "LEU" : [[0, 8], [0, 1], [1, 9], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5], [5, 6], [5, 7],
           [4, 10], [4, 11], [5, 12], [6, 13], [6, 14], [6, 15], [7, 16], [7, 17], [7, 18]],
  "MET" : [[0, 8], [0, 1], [1, 9], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5], [5, 6], [6, 7],
           [4, 10], [4, 11], [5, 12], [5, 13], [7, 14], [7, 15], [7, 16]],
  "ASN" : [[0, 8], [0, 1], [1, 9], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5], [5, 6], [5, 7],
           [4, 10], [4, 11], [7, 12], [7, 13]],
  "PRO" : [[0, 1], [1, 7], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5], [5, 6], [6, 0],
           [4, 8], [4, 9], [5, 10], [5, 11], [6, 12], [6, 13]],
  "GLN" : [[0, 9], [0, 1], [1, 10], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5], [5, 6], [6, 7], [6, 8],
           [4, 11], [4, 12], [5, 13], [5, 14], [8, 15], [8, 16]],
  "ARG" : [[0, 11], [0, 1], [1, 12], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [8, 10],
           [4, 13], [4, 14], [5, 15], [5, 16], [6, 17], [6, 18], [7, 19], [9, 20], [9, 21], [10, 22], [10, 23]],
  "SER" : [[0, 6], [0, 1], [1, 7], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5],
           [4, 8], [4, 9], [5, 10]],
  "THR" : [[0, 7], [0, 1], [1, 8], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5], [4, 6],
           [4, 9], [5, 10], [6, 11], [6, 12], [6, 13]],
  "VAL" : [[0, 7], [0, 1], [1, 8], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5], [4, 6],
           [4, 9], [5, 10], [5, 11], [5, 12], [6, 13], [6, 14], [6,15]],
  "TRP" : [[0, 14], [0, 1], [1, 15], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5],
           [5, 6], [5, 7], [6, 8], [7, 9], [7, 10], [8, 9], [9, 11], [10, 12], [11, 13], [12, 13], # Cyclic section
           [4, 16], [4, 17], [6, 18], [8, 19], [10, 20], [11, 21], [12, 22], [13, 23]],
  "TYR" : [[0, 12], [0, 1], [1, 13], [1, 2], [2, 3], [1, 4], # BackboneLinkages
           [4, 5],
           [5, 6], [5, 7], [6, 8], [7, 9], [8, 10], [9, 10], [10, 11], # Cyclic section
           [4, 14], [4, 15], [6, 16], [7, 17], [8, 18], [9, 19], [10, 20]],
} # Rosetta writes backbone heavy atoms first, then R group heavy atoms then H


