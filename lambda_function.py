import json
import boto3
import email
from email import policy
from email.parser import HeaderParser
from utils import one_hot_encode, vectorize_sequences

ENDPOINT_NAME = 'sms-spam-classifier-mxnet-2022-04-18-01-00-23-470'
LENGTH = 9013

def lambda_handler(event, context):
    s3 = boto3.client("s3")
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    objkey = event["Records"][0]["s3"]["object"]["key"]

    file_obj = event["Records"][0]
    filename = str(file_obj["s3"]['object']['key'])
    #print("filename: ", filename)
    fileObj = s3.get_object(Bucket = bucket, Key=filename)
    #print("file has been gotten!")
    content = fileObj["Body"].read().decode('utf-8')
    subject = content.split('Subject: ')[1]
    subject = subject.split('\n')[0]

    date = content.split('Date: ')[1]
    date = date.split('\n')[0]

    sender = content.split('Return-Path: <')[1]
    sender = sender.split('>')[0]
    print (subject, date, sender)
    print("end_1")

    print("start")
    content_list = content.split('\n')
    texts = []
    start = False
    for line in content_list:
        if not start:
            if 'text/plain' in line:
                start = True
        else:
            if '--00' in line:
                start = False
            if start:
                texts.append(line)
    body = "".join(texts)
    print(" ".join(body.split()))
    print("end_2")

    runtime = boto3.Session().client(service_name='sagemaker-runtime',region_name='us-east-1')

    test_messages = [body]
    one_hot_test_messages = one_hot_encode(test_messages, LENGTH)
    encoded_test_messages = vectorize_sequences(one_hot_test_messages, LENGTH)
    payload = json.dumps(encoded_test_messages.tolist())
    response = runtime.invoke_endpoint(EndpointName = ENDPOINT_NAME, ContentType = 'application/json', Body = payload)
    resp = json.loads(response['Body'].read().decode())
    label = 'SPAM' if resp.get("predicted_label")[0][0] == 1 else 'HAM'
    probability = resp.get("predicted_probability")
    for key in resp:
        print(key, resp[key])
    print(resp.get("predicted_label"))


    message_template = \
    f"We received your email sent at {date} with the subject {subject}.\n\n" + \
    "Here is a 240 character sample of the email body: \n" + \
    f"{body}\n" + \
    f"The email was categorized as {label} with a {probability[0][0] * 100}% confidence."
    # message_template = ["<div>" + m + "</div>" for m in message_template]
    # message_template = "".join(message_template)
    message_body = message_template# message_template.format(EMAIL_RECEIVE_DATE = edate, EMAIL_SUBJECT = subject, EMAIL_BODY = body, CLASSIFICATION = label, CLASSIFICATION_CONFIDENCE_SCORE = probability[0][0] * 100)
    print(message_body)

    msg = {"Subject" : {"Data" : "Re: " + subject}, "Body" : {"Html":{"Data": message_body}}}

    ses = boto3.client('ses')
    response = ses.send_email(Source = 'project3@qweasd.me', Destination = {"ToAddresses":[sender]}, Message = msg)

    return response
