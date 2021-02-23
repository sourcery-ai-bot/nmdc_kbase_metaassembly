import os
import time
import unittest
from configparser import ConfigParser

from nmdc_metaassembly.assemble import nmdc_mg_assembly
from unittest.mock import patch, MagicMock

import shutil

class mock_special:
    def __init__(self, tdir='test/data/', dst='/tmp'):
        self.tdir = tdir
        self.dst = dst

    def wdl(self, params):
        print(params)
        shutil.copy(os.path.join(self.tdir, 'data', 'meta.json'),self.dst)

        print(self.tdir)


class aassemblyTest(unittest.TestCase):

    mock_download_reads = {
            '53587/1/1': {
                'ref': '53587/1/1',
                'single_genome': 'true',
                'read_orientation_outward': 'false',
                'insert_size_mean': None,
                'insert_size_std_dev': None,
                'source': None,
                'strain': None,
                'sequencing_tech': 'Illumina',
                'read_count': 2500,
                'read_size': None,
                'gc_content': 0.680846,
                'total_bases': 250000,
                'read_length_mean': 100.0,
                'read_length_stdev': 0.0,
                'phred_type': '33',
                'number_of_duplicates': 11,
                'qual_min': 10.0,
                'qual_max': 51.0,
                'qual_mean': 43.0606,
                'qual_stdev': 10.5302,
                'base_percentages': {
                    'A': 16.0606,
                    'C': 34.1326,
                    'G': 33.952,
                    'N': 0.0,
                    'T': 15.8549},
                'files': {
                    'fwd': '/kb/module/work/tmp/c4714f1a-8482-4500-9519-5dd2d913495c.inter.fastq',
                    'fwd_name': 'small.inter.fq.gz',
                    'rev': None,
                    'rev_name': None,
                    'otype': 'interleaved',
                    'type': 'interleaved'}
                }
            }

    @classmethod
    def setUpClass(cls):
        cls.tdir=os.path.dirname(os.path.realpath(__file__))
        cls.wdl=cls.tdir + "/../metaAssembly/"

        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def xtest_assemble(self):
        asu = nmdc_mg_assembly('http://localhost', '/tmp', wdl=self.wdl)
        rv = {'files': self.mock_download_reads}
        asu.ru.download_reads = MagicMock(return_value=rv)
        asu.special = mock_special(tdir=self.tdir)
        asu.au.save_assembly_from_fasta = MagicMock()
        rep_rv = {
                "name": "bogus_report",
                "ref": "1/2/3"
                }
        asu.report.create = MagicMock(return_value=rep_rv)
        p = {
                "reads_upa": ['1/2/3'],
                "workspace_name": "bogus",
                "output_assembly_name": "bogus_assembly"
            }
        asu.assemble(p)

