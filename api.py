import json
import os
import time
import typing

import avro.datafile
import avro.io
import avro.schema
import requests


AVRO_SCHEMA = {
    'type': 'record',
    'name': 'Delivery',
    'namespace': 'com.dowjones.dna.avro',
    'doc': 'Avro schema for extraction content used by Dow Jones\' SyndicationHub',
    'fields': [
        {'name': 'an', 'type': ['string', 'null']},
        {'name': 'modification_datetime', 'type': ['long', 'null']},
        {'name': 'ingestion_datetime', 'type': ['long', 'null']},
        {'name': 'publication_date', 'type': ['long', 'null']},
        {'name': 'publication_datetime', 'type': ['long', 'null']},
        {'name': 'snippet', 'type': ['string', 'null']},
        {'name': 'body', 'type': ['string', 'null']},
        {'name': 'art', 'type': ['string', 'null']},
        {'name': 'action', 'type': ['string', 'null']},
        {'name': 'credit', 'type': ['string', 'null']},
        {'name': 'byline', 'type': ['string', 'null']},
        {'name': 'document_type', 'type': ['string', 'null']},
        {'name': 'language_code', 'type': ['string', 'null']},
        {'name': 'title', 'type': ['string', 'null']},
        {'name': 'copyright', 'type': ['string', 'null']},
        {'name': 'dateline', 'type': ['string', 'null']},
        {'name': 'source_code', 'type': ['string', 'null']},
        {'name': 'modification_date', 'type': ['long', 'null']},
        {'name': 'section', 'type': ['string', 'null']},
        {'name': 'company_codes', 'type': ['string', 'null']},
        {'name': 'publisher_name', 'type': ['string', 'null']},
        {'name': 'region_of_origin', 'type': ['string', 'null']},
        {'name': 'word_count', 'type': ['int', 'null']},
        {'name': 'subject_codes', 'type': ['string', 'null']},
        {'name': 'region_codes', 'type': ['string', 'null']},
        {'name': 'industry_codes', 'type': ['string', 'null']},
        {'name': 'person_codes', 'type': ['string', 'null']},
        {'name': 'currency_codes', 'type': ['string', 'null']},
        {'name': 'market_index_codes', 'type': ['string', 'null']},
        {'name': 'company_codes_about', 'type': ['string', 'null']},
        {'name': 'company_codes_association', 'type': ['string', 'null']},
        {'name': 'company_codes_lineage', 'type': ['string', 'null']},
        {'name': 'company_codes_occur', 'type': ['string', 'null']},
        {'name': 'company_codes_relevance', 'type': ['string', 'null']},
        {'name': 'source_name', 'type': ['string', 'null']}
    ]
}

READ_SCHEMA = avro.schema.Parse(json.dumps(AVRO_SCHEMA))


class DnaApiError(Exception):
    pass


class DnaApiKeyCheckError(DnaApiError):
    pass


class DnaApiJobError(DnaApiError):
    pass


class DnaApiDownloadError(DnaApiError):
    pass


class DnaApi:
    ACCOUNT_URL = 'https://api.dowjones.com/alpha/accounts/{0}'
    EXPLAIN_URL = 'https://api.dowjones.com/alpha/extractions/documents/_explain'
    SNAPSHOT_URL = 'https://api.dowjones.com/alpha/extractions/documents/'
    LIST_SNAPSHOTS_URL = 'https://api.dowjones.com/alpha/extractions/'

    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            'user-key': self.api_key,
            'content-type': 'application/json',
            'cache-control': 'no-cache'
        }
        self.account_data = {}

    def _check_api_key(self):
        response = requests.get(self.ACCOUNT_URL.format(self.api_key), headers=self.headers)
        response_content = response.json()
        try:
            errors = response_content['errors'][0]['detail']
            raise DnaApiKeyCheckError(errors)
        except KeyError:
            return response_content['data']

    def check(self):
        self.account_data = self._check_api_key()

    def _run_job(self, query, url, job_class):
        response = requests.post(url, data=json.dumps(query), headers=self.headers)
        response_content = response.json()
        try:
            errors = response_content['errors'][0]['detail']
            raise DnaApiJobError(errors)
        except KeyError:
            job_status_url = response_content["links"]["self"]
            job_data = response_content['data']
            return job_class(self.headers, job_status_url, job_data)

    def run_explanation_job(self, query):
        return self._run_job(query, self.EXPLAIN_URL, Job)

    def run_create_snapshot_job(self, query):
        return self._run_job(query, self.SNAPSHOT_URL, SnapshotCreateJob)

    def list_snapshots(self):
        response = requests.get(self.LIST_SNAPSHOTS_URL, headers=self.headers)
        response_content = response.json()
        try:
            errors = response_content['errors'][0]['detail']
            raise DnaApiError(errors)
        except KeyError:
            return [
                SnapshotResult.from_dict(self.headers, data)
                for data in response_content['data']
                if data['attributes']['extraction_type'] == 'documents'
            ]


class ExplanationResult(typing.NamedTuple):
    headers: dict
    id: str
    counts: int
    state: str

    @classmethod
    def from_dict(cls, headers, data):
        return cls(
            headers,
            data['id'],
            data['attributes']['counts'],
            data['attributes']['current_state']
        )


class SnapshotResult(typing.NamedTuple):
    headers: dict
    id: str
    state: str
    extraction_type: str
    type: str
    link: str

    @classmethod
    def from_dict(cls, headers, data):
        return cls(
            headers,
            data['id'],
            data['attributes']['current_state'],
            data['attributes']['extraction_type'],
            data['type'],
            data['links']['self']
        )

    def download(self, directory, filename_beginning='file', verbose=True):
        os.makedirs(directory, exist_ok=True)
        response = requests.get(self.link, headers=self.headers)
        response_content = response.json()
        try:
            errors = response_content['errors'][0]['detail']
            raise DnaApiDownloadError(errors)
        except KeyError:
            for idx, file_data in enumerate(response_content['data']['attributes']['files']):
                filename = '{}_{}.avro'.format(filename_beginning, idx)
                file_path = os.path.join(directory, filename)
                self._download_file(file_data['uri'], file_path, verbose)
        return Dataset(directory)

    def _download_file(self, url, path, verbose):
        response = requests.get(url, headers=self.headers, allow_redirects=True, stream=True)
        if verbose:
            file_size = response.headers['Content-length']
            print('Downloading file of size {}'.format(file_size))
        with open(path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1000000000):
                file.write(chunk)
        if verbose:
            print('Downloading finished. File {}.'.format(path))


class Job:
    class Status:
        CREATED = 'JOB_CREATED'
        QUEUED = 'JOB_QUEUED'
        VALIDATING = 'JOB_VALIDATING'
        RUNNING = 'JOB_STATE_RUNNING'
        DONE = 'JOB_STATE_DONE'
        ERROR = 'JOB_STATE_ERROR'

    default_sleep_time = 10
    result_class = ExplanationResult

    def __init__(self, headers, status_url, data):
        self.headers = headers
        self.status_url = status_url
        self.data = data
        self.status = data['attributes']['current_state']

    def _check_status(self):
        response = requests.get(self.status_url, headers=self.headers)
        response_content = response.json()
        try:
            self.data = response_content
            self.status = response_content['data']['attributes']['current_state']
        except KeyError:
            self.data = response_content
            self.status = self.Status.ERROR
        return self.status

    def wait_until_complete(self, verbose=True, sleep_time=None):
        sleep_time = sleep_time or self.default_sleep_time
        status = self._check_status()
        while status not in (self.Status.DONE, self.Status.ERROR):
            if verbose:
                print('{}...'.format(status))
            time.sleep(sleep_time)
            status = self._check_status()
        try:
            return self.result_class.from_dict(self.headers, self.data['data'])
        except KeyError:
            raise DnaApiJobError


class SnapshotCreateJob(Job):
    default_sleep_time = 60
    result_class = SnapshotResult


class Dataset:
    def __init__(self, directory):
        self.directory = directory
        self.files = sorted(
            [os.path.join(directory, file) for file in os.listdir(directory)],
            key=lambda name: int(''.join(char for char in name if char.isdigit()))
        )

    def records(self):
        datum_reader = avro.io.DatumReader(READ_SCHEMA)
        for file in self.files:
            with avro.datafile.DataFileReader(open(file, "rb"), datum_reader) as reader:
                for record in reader:
                    yield record
