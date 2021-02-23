/*
A KBase module: nmdc_metaassembly
*/

module nmdc_metaassembly {
    typedef structure {
        string report_name;
        string report_ref;
    } ReportResults;

    /*
        This example function accepts any number of parameters and returns results in a KBaseReport
    */
    funcdef run_nmdc_metaassembly(mapping<string,UnspecifiedObject> params) returns (ReportResults output) authentication required;

};
