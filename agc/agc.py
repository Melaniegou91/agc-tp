#!/bin/env python3
# -*- coding: utf-8 -*-
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    A copy of the GNU General Public License is available at
#    http://www.gnu.org/licenses/gpl-3.0.html

"""OTU clustering"""

import argparse
import sys
import os
import gzip
import statistics
import textwrap
import numpy as np
np.int = int 
from pathlib import Path
from collections import Counter
from typing import Iterator, Dict, List
# https://github.com/briney/nwalign3
# ftp://ftp.ncbi.nih.gov/blast/matrices/
import nwalign3 as nw

__author__ = "Your Name"
__copyright__ = "Universite Paris Diderot"
__credits__ = ["Your Name"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Your Name"
__email__ = "your@email.fr"
__status__ = "Developpement"



def isfile(path: str) -> Path:  # pragma: no cover
    """Check if path is an existing file.

    :param path: (str) Path to the file

    :raises ArgumentTypeError: If file does not exist

    :return: (Path) Path object of the input file
    """
    myfile = Path(path)
    if not myfile.is_file():
        if myfile.is_dir():
            msg = f"{myfile.name} is a directory."
        else:
            msg = f"{myfile.name} does not exist."
        raise argparse.ArgumentTypeError(msg)
    return myfile


def get_arguments(): # pragma: no cover
    """Retrieves the arguments of the program.

    :return: An object that contains the arguments
    """
    # Parsing arguments
    parser = argparse.ArgumentParser(description=__doc__, usage=
                                     "{0} -h"
                                     .format(sys.argv[0]))
    parser.add_argument('-i', '-amplicon_file', dest='amplicon_file', type=isfile, required=True, 
                        help="Amplicon is a compressed fasta file (.fasta.gz)")
    parser.add_argument('-s', '-minseqlen', dest='minseqlen', type=int, default = 400,
                        help="Minimum sequence length for dereplication (default 400)")
    parser.add_argument('-m', '-mincount', dest='mincount', type=int, default = 10,
                        help="Minimum count for dereplication  (default 10)")
    parser.add_argument('-o', '-output_file', dest='output_file', type=Path,
                        default=Path("OTU.fasta"), help="Output file")
    return parser.parse_args()


def read_fasta(amplicon_file: Path, minseqlen: int) -> Iterator[str]:
    """Read a compressed fasta and extract all fasta sequences.

    :param amplicon_file: (Path) Path to the amplicon file in FASTA.gz format.
    :param minseqlen: (int) Minimum amplicon sequence length
    :return: A generator object that provides the Fasta sequences (str).
    """
    with gzip.open(amplicon_file, "rt") as  file:
        seq = ""
        for line in file:
            if not line.startswith(">"):
                seq+=line.strip()
            else: 
                if len(seq) >= minseqlen :
                    yield(seq) 
                seq =""      
    if len(seq) >= minseqlen :
        yield(seq)         
     

def dereplication_fulllength(amplicon_file: Path, minseqlen: int, mincount: int) -> Iterator[List]:
    """Dereplicate the set of sequence

    :param amplicon_file: (Path) Path to the amplicon file in FASTA.gz format.
    :param minseqlen: (int) Minimum amplicon sequence length
    :param mincount: (int) Minimum amplicon count
    :return: A generator object that provides a (list)[sequences, count] of sequence with a count >= mincount and a length >= minseqlen.
    """
    seq_sim_counts = {}
    for seq in read_fasta(amplicon_file, minseqlen):
        seq_sim_counts[seq]=0
    for seq in read_fasta(amplicon_file, minseqlen):
        seq_sim_counts[seq]+=1
    key_sorted = sorted(seq_sim_counts , key = seq_sim_counts.get ,reverse = True)
    for k in key_sorted :
        if seq_sim_counts[k] >= mincount :
            yield k,seq_sim_counts[k]


def get_identity(alignment_list: List[str]) -> float:
    """Compute the identity rate between two sequences

    :param alignment_list:  (list) A list of aligned sequences in the format ["SE-QUENCE1", "SE-QUENCE2"]
    :return: (float) The rate of identity between the two sequences.
    """
    cpt_nucl_identique = 0
    for i in range(len(alignment_list[0])) : 
        if alignment_list[0][i] == alignment_list[1][i]:
            cpt_nucl_identique+=1
    id = (cpt_nucl_identique / len(alignment_list[0]))*100
    return id


def abundance_greedy_clustering(amplicon_file: Path, minseqlen: int, mincount: int, chunk_size: int, kmer_size: int) -> List:
    """Compute an abundance greedy clustering regarding sequence count and identity.
    Identify OTU sequences.

    :param amplicon_file: (Path) Path to the amplicon file in FASTA.gz format.
    :param minseqlen: (int) Minimum amplicon sequence length.
    :param mincount: (int) Minimum amplicon count.
    :param chunk_size: (int) A fournir mais non utilise cette annee
    :param kmer_size: (int) A fournir mais non utilise cette annee
    :return: (list) A list of all the [OTU (str), count (int)] .
    """
    OTU =[]
    count_repl = dereplication_fulllength(amplicon_file, minseqlen, mincount)

    for sequence, count in count_repl :
        is_OTU = True
        for otu_seq, otu_count in OTU :
            align = nw.global_align(sequence, otu_seq, matrix=str(Path(__file__).parent / "MATCH"))
            id = get_identity(align)
            if id < 97 : 
                is_OTU = True
                break
            else :
                is_OTU = False
        if is_OTU :
            OTU.append([sequence,count])
    return OTU


def write_OTU(OTU_list: List, output_file: Path) -> None:
    """Write the OTU sequence in fasta format.

    :param OTU_list: (list) A list of OTU sequences
    :param output_file: (Path) Path to the output file
    """
    with open(output_file,"w") as file:
        cpt = 1
        for i in range(len(OTU_list)) :
            file.write(f">OTU_{cpt} occurrence:{OTU_list[i][1]}\n")
            file.write(textwrap.fill(OTU_list[i][0], width=80))
            file.write("\n")
            cpt+=1


#==============================================================
# Main program
#==============================================================
def main(): # pragma: no cover
    """
    Main program function
    """
    # Get arguments
    args = get_arguments()
    # Votre programme ici
    amplicon_file = args.amplicon_file
    minseqlen = 400
    mincount = 10

    chunk_size = 0
    kmer_size = 0
    OTU_list = abundance_greedy_clustering(amplicon_file,
                                           minseqlen,
                                           mincount,
                                           chunk_size,
                                           kmer_size)
    write_OTU(OTU_list,args.output_file)
    print("Done")

if __name__ == '__main__':
    main()
