
import json
import boto3
import io
from pypdf import PdfReader as Re
from common.ingest import ingest_extracted_text



def extract_text(file_stream):
    """Extract text from a PDF file stream and return as a string."""
    try:
        reader = Re(file_stream)
    except Exception as e:
        print(f"Error reading PDF file: {e}")
        return {
            'statusCode': 422,
            'body': json.dumps({'error': str(e)})
        } 
    extracted_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    return extracted_text

def handler(event, context):
    print("Received PDF file in event.")
    print(f"Received event: {json.dumps(event)}")

    try:
        # Retrieve PDF file from S3 using the event data
        s3 = boto3.client('s3')
        file_obj = s3.get_object(Bucket=event['bucket'], Key=event['file_key'])
        file_content = file_obj['Body'].read()

        # Step 2: Extract text from the PDF
        extracted_text = extract_text(io.BytesIO(file_content))

        if not extracted_text:
            raise ValueError("Extracted text is empty")

        # Extract docketId, commentId, and attachmentId from the file_key
        file_key = event['file_key']
        parts = file_key.split('/')

        # Extract docketId, commentId, and attachmentId based on file structure
        docketId = parts[2]  # Assuming docketId is always in this position (e.g. "APHIS-2022-0055")
        filename = parts[-1]  # Get the filename
        commentId = filename.split('_')[0]  # Extract commentId (e.g. "APHIS-2022-0055-0002" from "APHIS-2022-0055-0002_attachment_1.pdf")
        attachmentId = commentId + "-" + filename.split('_')[-1].replace('.pdf', '')  # Extract attachmentId (e.g. "APHIS-2022-0055-0002-1" from "APHIS-2022-0055-0002_attachment_1.pdf")

        # Construct the dictionary with the extracted text and other necessary data
        data = {
            "extractedText": extracted_text,
            "docketId": docketId,  # Extracted from the file_key
            "commentId": commentId,  # Extracted from the file_key
            "attachmentId": attachmentId,   # Extracted from the file_key
            "extractedMethod": "pypdf",  # Indicating the library used for extraction            
        }
        
        print(f"Extracted data: {data}")

        # Check if the event is related to comments_attachments
        if 'comments_attachments' in event['file_key']:
            # Ingest the extracted text and the prepared data
            print("Ingesting extracted text...")
            ingest_extracted_text(data)  # Pass the dictionary to the ingest function
            print("Ingestion complete!")

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Data processed successfully'})
        }

    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': str(e)})
        }