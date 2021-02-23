from installed_clients.KBaseReportClient import KBaseReport
from installed_clients.specialClient import special
from installed_clients.ReadsUtilsClient import ReadsUtils
from installed_clients.AssemblyUtilClient import AssemblyUtil
import shutil
import json
import os

class nmdc_mg_assembly:
    def __init__(self, callbaack_url, scratch, wdl='../metaAssembly/'):
        self.callback_url = callbaack_url
        self.scratch  = scratch
        self.special = special(self.callback_url)
        self.ru = ReadsUtils(self.callback_url)
        self.au = AssemblyUtil(self.callback_url)
        self.report = KBaseReport(self.callback_url)
        self.wdl_base = wdl

    def validate_params(self, params):
        pass

    def fetch_reads_files(self, reads_upas):
        """
        From a list of reads UPAs, uses ReadsUtils to fetch the reads as files.
        Returns them as a dictionary from reads_upa -> filename
        """
        if reads_upas is None:
            raise ValueError("reads_upas must be a list of UPAs")
        if len(reads_upas) == 0:
            raise ValueError("reads_upas must contain at least one UPA")
        reads_info = self.ru.download_reads(({
            'read_libraries': reads_upas,
            'interleaved': 'true',
            'gzipped': None
        }))['files']
        file_set = dict()
        for reads in reads_info:
            file_set[reads] = reads_info[reads]['files']['fwd']
        return file_set


    def run_wdl(self, rf):
        print(os.getcwd())
        wdl_files = [
                'jgi_assembly.wdl'
                ]
               
        for f in wdl_files:
            src = self.wdl_base + f
            dst = './' + f
            shutil.copy(src, dst)
        ins = {
                "jgi_metaASM.input_file": [rf],
                "jgi_metaASM.rename_contig_prefix":"contig",
                "jgi_metaASM.outdir":"/out/"
        }
        input_file = os.path.join(self.scratch, 'inputs.json')
        with open(input_file, 'w') as f:
            f.write(json.dumps(ins))

        p = {
            'workflow': wdl_files[0],
            'inputs': input_file
        }

        res = self.special.wdl(p)
        print('wdl: '+str(res))

    def upload_assembly(self, file_path, workspace_name, assembly_name):
        """
        From a list of file paths, uploads them to KBase, generates Assembly objects,
        then returns the generated UPAs.
        """
        if not file_path:
            raise ValueError("file_path must be defined")
        if not os.path.exists(file_path):
            raise ValueError("The given assembly file '{}' does not exist".format(file_path))
        if not workspace_name:
            raise ValueError("workspace_name must be defined")
        if not assembly_name:
            raise ValueError("assembly_name must be defined")

        assembly_upa = self.au.save_assembly_from_fasta({
            "file": {
                "path": file_path
            },
            "workspace_name": workspace_name,
            "assembly_name": assembly_name
        })
        return assembly_upa

    def _upload_pipeline_result(self, pipeline_result, workspace_name, assembly_name,
                                filtered_reads_name=None,
                                cleaned_reads_name=None,
                                skip_rqcfilter=False,
                                input_reads=None):
        """
        This is very tricky and uploads (optionally!) a few things under different cases.
        1. Uploads assembly
            - this always happens after a successful run.
        2. Cleaned reads - passed RQCFilter / BFC / SeqTK
            - optional, if cleaned_reads_name isn't None
        3. Filtered reads - passed RQCFilter
            - optional, if filtered_reads_name isn't None AND skip_rqcfilter is False
        returns a dict of UPAs with the following keys:
        - assembly_upa - the assembly (always)
        - filtered_reads_upa - the RQCFiltered reads (optionally)
        - cleaned_reads_upa - the RQCFiltered -> BFC -> SeqTK cleaned reads (optional)
        """

        # upload the assembly
        uploaded_assy_upa = self.file_util.upload_assembly(
            pipeline_result["spades"]["contigs_file"], workspace_name, assembly_name
        )
        upload_result = {
            "assembly_upa": uploaded_assy_upa
        }
        # upload filtered reads if we didn't skip RQCFilter (otherwise it's just a copy)
        if filtered_reads_name and not skip_rqcfilter:
            # unzip the cleaned reads because ReadsUtils won't do it for us.
            decompressed_reads = os.path.join(self.output_dir, "filtered_reads.fastq")
            pigz_command = "{} -d -c {} > {}".format(PIGZ, pipeline_result["rqcfilter"]["filtered_fastq_file"], decompressed_reads)
            p = subprocess.Popen(pigz_command, cwd=self.scratch_dir, shell=True)
            exit_code = p.wait()
            if exit_code != 0:
                raise RuntimeError("Unable to decompress filtered reads for validation! Can't upload them, either!")
            filtered_reads_upa = self.file_util.upload_reads(
                decompressed_reads, workspace_name, filtered_reads_name, input_reads
            )
            upload_result["filtered_reads_upa"] = filtered_reads_upa
        # upload the cleaned reads
        if cleaned_reads_name:
            # unzip the cleaned reads because ReadsUtils won't do it for us.
            decompressed_reads = os.path.join(self.output_dir, "cleaned_reads.fastq")
            pigz_command = "{} -d -c {} > {}".format(PIGZ, pipeline_result["seqtk"]["cleaned_reads"], decompressed_reads)
            p = subprocess.Popen(pigz_command, cwd=self.scratch_dir, shell=True)
            exit_code = p.wait()
            if exit_code != 0:
                raise RuntimeError("Unable to decompress cleaned reads for validation! Can't upload them, either!")
            cleaned_reads_upa = self.file_util.upload_reads(
                decompressed_reads, workspace_name, cleaned_reads_name, input_reads
            )
            upload_result["cleaned_reads_upa"] = cleaned_reads_upa
        return upload_result


    def assemble(self, params):
        self.validate_params(params)
        workspace_name = params['workspace_name']
        assembly_name = params['output_assembly_name']

        # Stage Data
        files = self.fetch_reads_files([params["reads_upa"]])
        reads_files = list(files.values())

        # Run WDL
        self.run_wdl(reads_files[0])

        # Check if things ran
        mfile = os.path.join(self.scratch, 'meta.json')
        print(mfile)
        if not os.path.exists(mfile):
            raise OSError("Failed to run workflow")

        with open(mfile) as f:
            pipeline_output = json.loads(f.read())
        out = pipeline_output["calls"]["jgi_metaASM.create_agp"][0]["outputs"]
        print(out)
 

        # Generate Output Objects
        contigs_fn = out['outcontigs']
        upa = self.upload_assembly(contigs_fn, workspace_name, assembly_name)

        upload_kwargs = {
        }

        print("upload complete")


        # Do report
        report_info = self.report.create({'report': {'objects_created':[],
                                                'text_message': "Assemble metagenomic reads"},
                                                'workspace_name': workspace_name})
        return {
            'report_name': report_info['name'],
            'report_ref': report_info['ref'],
        }
