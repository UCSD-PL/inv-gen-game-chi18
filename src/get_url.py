#! /usr/bin/env python
from traceback import print_exc
from mturk_util import error, connect, mkParser


p = mkParser("Download a file from a question answer")
p.add_argument('AssignmentId', type=str, help='Id of the Assignment.')
p.add_argument('QuestionId', type=str, help='Id of the question.')
args = p.parse_args()

try:
    mc = connect(args.credentials_file, args.sandbox, True)
    r = mc.get_file_upload_url(args.AssignmentId, args.QuestionId)
    print r[0].FileUploadURL
except Exception,e:
    print_exc()
    error("Failed...")
