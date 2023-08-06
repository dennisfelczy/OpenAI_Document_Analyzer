# Description: This script analyzes a document with the Form Recognizer Document Analysis API utilizing the General Document Model. The results are written to a json file to files/forms_result.json
import os
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.core.serialization import AzureJSONEncoder
from dotenv import load_dotenv, find_dotenv
import json
    

# loads the environment variables from the .env file
load_dotenv(find_dotenv(), override=True)

endpoint = os.environ["FORMS_ENDPOINT"]
key = os.environ["FORMS_KEY"]

def format_bounding_region(bounding_regions):
    if not bounding_regions:
        return "N/A"
    return ", ".join("Page #{}: {}".format(region.page_number, format_polygon(region.polygon)) for region in bounding_regions)

def format_polygon(polygon):
    if not polygon:
        return "N/A"
    return ", ".join(["[{}, {}]".format(p.x, p.y) for p in polygon])


def analyze_general_documents(projectname,documentname):
    # sample document
    #docUrl = "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/sample-layout.pdf"

    # create your `DocumentAnalysisClient` instance and `AzureKeyCredential` variable
    document_analysis_client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    #analyze document from url
    #poller = document_analysis_client.begin_analyze_document_from_url(
    #        "prebuilt-document", docUrl)
    #result = poller.result()
    
    #analyze document from local file
    with open("projects/"+projectname+'/files/'+documentname, "rb") as f:
        print("Analyzing document...")
        poller = document_analysis_client.begin_analyze_document("prebuilt-document", f)
        result = poller.result()
    
    analyze_result_dict = result.to_dict()
    #write results to json file
    jsonfile = "projects/"+projectname+'/files/'+documentname+'.json'
    with open(jsonfile, 'w', encoding='utf-8') as f:
        print("Writing results to json file...")
        json.dump(analyze_result_dict, f, cls=AzureJSONEncoder, ensure_ascii=False, indent=4)
    return jsonfile   
    
"""     for style in result.styles:
        if style.is_handwritten:
            print("Document contains handwritten content: ")
            print(",".join([result.content[span.offset:span.offset + span.length] for span in style.spans]))

    print("----Key-value pairs found in document----")
    for kv_pair in result.key_value_pairs:
        if kv_pair.key:
            print(
                    "Key '{}' found within '{}' bounding regions".format(
                        kv_pair.key.content,
                        format_bounding_region(kv_pair.key.bounding_regions),
                    )
                )
        if kv_pair.value:
            print(
                    "Value '{}' found within '{}' bounding regions\n".format(
                        kv_pair.value.content,
                        format_bounding_region(kv_pair.value.bounding_regions),
                    )
                )

    for page in result.pages:
        print("----Analyzing document from page #{}----".format(page.page_number))
        print(
            "Page has width: {} and height: {}, measured with unit: {}".format(
                page.width, page.height, page.unit
            )
        )

        for line_idx, line in enumerate(page.lines):
            print(
                "...Line # {} has text content '{}' within bounding box '{}'".format(
                    line_idx,
                    line.content,
                    format_polygon(line.polygon),
                )
            )

        for word in page.words:
            print(
                "...Word '{}' has a confidence of {}".format(
                    word.content, word.confidence
                )
            )

        for selection_mark in page.selection_marks:
            print(
                "...Selection mark is '{}' within bounding box '{}' and has a confidence of {}".format(
                    selection_mark.state,
                    format_polygon(selection_mark.polygon),
                    selection_mark.confidence,
                )
            )

    for table_idx, table in enumerate(result.tables):
        print(
            "Table # {} has {} rows and {} columns".format(
                table_idx, table.row_count, table.column_count
            )
        )
        for region in table.bounding_regions:
            print(
                "Table # {} location on page: {} is {}".format(
                    table_idx,
                    region.page_number,
                    format_polygon(region.polygon),
                )
            )
        for cell in table.cells:
            print(
                "...Cell[{}][{}] has content '{}'".format(
                    cell.row_index,
                    cell.column_index,
                    cell.content,
                )
            )
            for region in cell.bounding_regions:
                print(
                    "...content on page {} is within bounding box '{}'\n".format(
                        region.page_number,
                        format_polygon(region.polygon),
                    )
                )
    print("----------------------------------------") """


if __name__ == "__main__":
    print("Running general document analysis...")
    analyze_general_documents("files/DWS Annual Report 2022_EN.pdf")