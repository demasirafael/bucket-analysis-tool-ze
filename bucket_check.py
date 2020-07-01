import boto3
import json
import sys

s3 = boto3.client('s3',
                  aws_access_key_id=sys.argv[1],
                  aws_secret_access_key=sys.argv[2],
                  region_name="us-east-1"
                  )
pricing = boto3.client('pricing',
                       aws_access_key_id=sys.argv[1],
                       aws_secret_access_key=sys.argv[2],
                       region_name="us-east-1"
                       )
locationdict = {
    "None": 'US East (N. Virginia)',
    "us-east-2": 'US East (Ohio)',
    "us-west-1": 'US West (N. California)',
    "us-west-2": 'US West (Oregon)',
    "af-south-1": 'Africa (Cape Town)',
    "ap-east-1": 'Asia Pacific (Hong Kong)',
    "ap-south-1": 'Asia Pacific (Mumbai)',
    "ap-northeast-2": 'Asia Pacific (Seoul)',
    "ap-southeast-1": 'Asia Pacific (Singapore)',
    "ap-southeast-2": 'Asia Pacific (Sydney)',
    "ap-northeast-1": 'Asia Pacific (Tokyo)',
    "ca-central-1": 'Canada (Central)',
    "eu-central-1": 'EU (Frankfurt)',
    "eu-west-1": 'EU (Ireland)',
    "eu-west-2": 'EU (London)',
    "eu-south-1": 'EU (Milan)',
    "eu-west-3": 'EU (Paris)',
    "eu-north-1": 'EU (Stockholm)',
    "me-south-1": 'Middle East (Bahrain)',
    "sa-east-1": 'South America (Sao Paulo)'
}

storagetypedict = {
    "STANDARD": 'Standard',
    "STANDARD_IA": 'Standard - Infrequent Access',
    "ONEZONE_IA": 'One Zone - Infrequent Access',
    "INTELLIGENT_TIERING": 'Intelligent-Tiering Frequent Access',
    "DEEP_ARCHIVE": 'Glacier Deep Archive',
    "GLACIER": 'Glacier'
}


def listbucketobjects(bucket):
    objectsList = s3.list_objects_v2(
        Bucket=bucket['Name'],
    )

    if objectsList['IsTruncated']:
        objectslistcont = s3.list_objects_v2(
            Bucket=bucket['Name'],
            ContinuationToken=objectsList['NextContinuationToken']
        )
        objectsList['Contents'] = objectsList['Contents'] + objectslistcont['Contents']

    if 'Contents' in objectsList:
        return objectsList['Contents']
    else:
        objects = {}
        return objects


def getbucketsize(bucketobjects):
    total_size = 0
    totalbystorage = dict()
    for object in bucketobjects:
        if object['StorageClass'] in totalbystorage:
            totalbystorage[object['StorageClass']] = (totalbystorage[object['StorageClass']] + object['Size'] / 1000)
        else:
            totalbystorage[object['StorageClass']] = (object['Size'] / 1000)
        total_size = total_size + object['Size']
    return total_size, totalbystorage


def get_price_average(volumetype, location):
    s3Prices = pricing.get_products(
        ServiceCode='AmazonS3',
        Filters=[
            {
                'Type': 'TERM_MATCH',
                'Field': 'ServiceCode',
                'Value': 'AmazonS3',
            },
            {
                'Type': 'TERM_MATCH',
                'Field': 'location',
                'Value': location,
            },
            {
                'Type': 'TERM_MATCH',
                'Field': 'volumeType',
                'Value': volumetype,
            },
        ],
        FormatVersion='aws_v1',
    )

    s3PricesParsed = json.loads(s3Prices['PriceList'][0])

    price_average = 0

    for key in s3PricesParsed['terms']['OnDemand']:
        for x in s3PricesParsed['terms']['OnDemand'][key]['priceDimensions']:
            price_average = price_average + float(
                s3PricesParsed['terms']['OnDemand'][key]['priceDimensions'][x]['pricePerUnit']['USD'])

    return price_average / 3


bucketslist = s3.list_buckets()

for bucket in bucketslist['Buckets']:
    location = s3.get_bucket_location(
        Bucket=bucket['Name']
    )
    print("-----------BUCKET--------------")
    print("Bucket Name: ", bucket['Name'])
    print("Creation Date: ", bucket['CreationDate'])
    print("Location: ", location['LocationConstraint'])
    bucketobjects = listbucketobjects(bucket)
    print("Amount of Objects: ", len(bucketobjects))
    if len(bucketobjects) > 0:
        print("Last Modified Object: ", bucketobjects[len(bucketobjects) - 1]['LastModified'])
        total_size = getbucketsize(bucketobjects)
        print("Total Size: ", total_size[0] / 1000, "KB")
        print("Size by storage type: ", total_size[1])
        price_total = 0
        for storagetype in total_size[1]:
            key, value = list(total_size[1].items())[0]
            price_average = get_price_average(storagetypedict[key], locationdict[location['LocationConstraint']])
            price = float((price_average * total_size[1][storagetype]) / 1000000)
            price_total = price_total + price
        print("Estimated Bucket Price: USD", format(price_total, '.12f'))
    else:
        print("Total Size: 0KB")
