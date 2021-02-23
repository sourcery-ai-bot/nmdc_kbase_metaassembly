# -*- coding: utf-8 -*-
import os
import time
import unittest
import json
from configparser import ConfigParser

from nmdc_metaassembly.nmdc_metaassemblyImpl import nmdc_metaassembly
from nmdc_metaassembly.nmdc_metaassemblyServer import MethodContext
from nmdc_metaassembly.authclient import KBaseAuth as _KBaseAuth

from installed_clients.WorkspaceClient import Workspace
from unittest.mock import MagicMock
import shutil

class mock_special:
    def __init__(self, tdir='/kb/module/test/data/', dst='/kb/module/work/tmp/'):
        self.tdir = tdir
        self.dst = dst
        self.fna = 'cromwell-executions/jgi_metaASM/08e31392-9a1f-4d7d-9bd3-3be3c4e7bb43/call-create_agp/execution/assembly_contigs.fna'

    def wdl(self, params):
        print("mock wdl called")
        fn = 'assembly_contigs.fna'
        contig_file = os.path.join(self.dst, fn)
        meta = {
                "calls": {
                   "jgi_metaASM.create_agp": [{
                      "outputs": {
                        "outcontigs": self.fna
                      }
                   }]
                }
              }
        src=os.path.join(self.tdir, self.fna)
        os.makedirs(os.path.dirname(self.fna))
        shutil.copy(src, self.fna)
        with open('/kb/module/work/tmp/meta.json', 'w') as f:
             f.write(json.dumps(meta))



class nmdc_metaassemblyTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        token = os.environ.get('KB_AUTH_TOKEN', None)
        config_file = os.environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('nmdc_metaassembly'):
            cls.cfg[nameval[0]] = nameval[1]
        # Getting username from Auth profile for token
        authServiceUrl = cls.cfg['auth-service-url']
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': token,
                        'user_id': user_id,
                        'provenance': [
                            {'service': 'nmdc_metaassembly',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        cls.wsURL = cls.cfg['workspace-url']
        cls.wsClient = Workspace(cls.wsURL)
        cls.serviceImpl = nmdc_metaassembly(cls.cfg)
        cls.scratch = cls.cfg['scratch']
        cls.callback_url = os.environ['SDK_CALLBACK_URL']
        suffix = int(time.time() * 1000)
        cls.wsName = "test_nmdc_mgassembly" + str(suffix)
        ret = cls.wsClient.create_workspace({'workspace': cls.wsName})  # noqa
        cls.testWS = 'KBaseTestData'
        cls.testReads = 'small.interlaced_reads'

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    # NOTE: According to Python unittest naming rules test method names should start from 'test'. # noqa
    def test_assembly(self):
        ret = self.wsClient.copy_object({'from': {'workspace': self.testWS, 'name': self.testReads}, 
                                            'to': {'workspace': self.wsName, 'name': self.testReads}})
        upa = '{}/{}/{}'.format(ret[6], ret[0], ret[4])
        rv = {}
        self.serviceImpl.asu.special = mock_special()
        params = {
                  'workspace_name': self.wsName,
                  "output_assembly_name": "test_assembly",
                  'reads_upa': upa
                 }
        ret = self.serviceImpl.run_nmdc_metaassembly(self.ctx, params)
