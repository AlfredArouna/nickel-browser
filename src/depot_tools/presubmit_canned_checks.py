# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Generic presubmit checks that can be reused by other presubmit checks."""

### Description checks

def CheckChangeHasTestField(input_api, output_api):
  """Requires that the changelist have a TEST= field."""
  if input_api.change.TEST:
    return []
  else:
    return [output_api.PresubmitNotifyResult(
        'If this change requires manual test instructions to QA team, add '
        'TEST=[instructions].')]


def CheckChangeHasBugField(input_api, output_api):
  """Requires that the changelist have a BUG= field."""
  if input_api.change.BUG:
    return []
  else:
    return [output_api.PresubmitNotifyResult(
        'If this change has an associated bug, add BUG=[bug number].')]


def CheckChangeHasTestedField(input_api, output_api):
  """Requires that the changelist have a TESTED= field."""
  if input_api.change.TESTED:
    return []
  else:
    return [output_api.PresubmitError('Changelist must have a TESTED= field.')]


def CheckChangeHasQaField(input_api, output_api):
  """Requires that the changelist have a QA= field."""
  if input_api.change.QA:
    return []
  else:
    return [output_api.PresubmitError('Changelist must have a QA= field.')]


def CheckDoNotSubmitInDescription(input_api, output_api):
  """Checks that the user didn't add 'DO NOT ' + 'SUBMIT' to the CL description.
  """
  keyword = 'DO NOT ' + 'SUBMIT'
  if keyword in input_api.change.DescriptionText():
    return [output_api.PresubmitError(
        keyword + ' is present in the changelist description.')]
  else:
    return []


def CheckChangeHasDescription(input_api, output_api):
  """Checks the CL description is not empty."""
  text = input_api.change.DescriptionText()
  if text.strip() == '':
    if input_api.is_committing:
      return [output_api.PresubmitError('Add a description.')]
    else:
      return [output_api.PresubmitNotifyResult('Add a description.')]
  return []

### Content checks

def CheckDoNotSubmitInFiles(input_api, output_api):
  """Checks that the user didn't add 'DO NOT ' + 'SUBMIT' to any files."""
  keyword = 'DO NOT ' + 'SUBMIT'
  # We want to check every text files, not just source files.
  for f, line_num, line in input_api.RightHandSideLines(lambda x: x):
    if keyword in line:
      text = 'Found ' + keyword + ' in %s, line %s' % (f.LocalPath(), line_num)
      return [output_api.PresubmitError(text)]
  return []


def CheckChangeLintsClean(input_api, output_api, source_file_filter=None):
  """Checks that all '.cc' and '.h' files pass cpplint.py."""
  _RE_IS_TEST = input_api.re.compile(r'.*tests?.(cc|h)$')
  result = []

  # Initialize cpplint.
  import cpplint
  # Access to a protected member _XX of a client class
  # pylint: disable=W0212
  cpplint._cpplint_state.ResetErrorCounts()

  # Justifications for each filter:
  #
  # - build/include       : Too many; fix in the future.
  # - build/include_order : Not happening; #ifdefed includes.
  # - build/namespace     : I'm surprised by how often we violate this rule.
  # - readability/casting : Mistakes a whole bunch of function pointer.
  # - runtime/int         : Can be fixed long term; volume of errors too high
  # - runtime/virtual     : Broken now, but can be fixed in the future?
  # - whitespace/braces   : We have a lot of explicit scoping in chrome code.
  cpplint._SetFilters('-build/include,-build/include_order,-build/namespace,'
                      '-readability/casting,-runtime/int,-runtime/virtual,'
                      '-whitespace/braces')

  # We currently are more strict with normal code than unit tests; 4 and 5 are
  # the verbosity level that would normally be passed to cpplint.py through
  # --verbose=#. Hopefully, in the future, we can be more verbose.
  files = [f.AbsoluteLocalPath() for f in
           input_api.AffectedSourceFiles(source_file_filter)]
  for file_name in files:
    if _RE_IS_TEST.match(file_name):
      level = 5
    else:
      level = 4

    cpplint.ProcessFile(file_name, level)

  if cpplint._cpplint_state.error_count > 0:
    if input_api.is_committing:
      res_type = output_api.PresubmitError
    else:
      res_type = output_api.PresubmitPromptWarning
    result = [res_type('Changelist failed cpplint.py check.')]

  return result


def CheckChangeHasNoCR(input_api, output_api, source_file_filter=None):
  """Checks no '\r' (CR) character is in any source files."""
  cr_files = []
  for f in input_api.AffectedSourceFiles(source_file_filter):
    if '\r' in input_api.ReadFile(f, 'rb'):
      cr_files.append(f.LocalPath())
  if cr_files:
    return [output_api.PresubmitPromptWarning(
        'Found a CR character in these files:', items=cr_files)]
  return []


def CheckSvnModifiedDirectories(input_api, output_api, source_file_filter=None):
  """Checks for files in svn modified directories.

  They will get submitted on accident because svn commits recursively by
  default, and that's very dangerous.
  """
  if input_api.change.scm != 'svn':
    return []

  errors = []
  current_cl_files = input_api.change.GetModifiedFiles()
  all_modified_files = input_api.change.GetAllModifiedFiles()
  # Filter out files in the current CL.
  modified_files = [f for f in all_modified_files if f not in current_cl_files]
  modified_abspaths = [input_api.os_path.abspath(f) for f in modified_files]

  for f in input_api.AffectedFiles(source_file_filter):
    if f.Action() == 'M' and f.IsDirectory():
      curpath = f.AbsoluteLocalPath()
      bad_files = []
      # Check if any of the modified files in other CLs are under curpath.
      for i in xrange(len(modified_files)):
        abspath = modified_abspaths[i]
        if input_api.os_path.commonprefix([curpath, abspath]) == curpath:
          bad_files.append(modified_files[i])
      if bad_files:
        if input_api.is_committing:
          error_type = output_api.PresubmitPromptWarning
        else:
          error_type = output_api.PresubmitNotifyResult
        errors.append(error_type(
            'Potential accidental commits in changelist %s:' % f.LocalPath(),
            items=bad_files))
  return errors


def CheckChangeHasOnlyOneEol(input_api, output_api, source_file_filter=None):
  """Checks the files ends with one and only one \n (LF)."""
  eof_files = []
  for f in input_api.AffectedSourceFiles(source_file_filter):
    contents = input_api.ReadFile(f, 'rb')
    # Check that the file ends in one and only one newline character.
    if len(contents) > 1 and (contents[-1:] != '\n' or contents[-2:-1] == '\n'):
      eof_files.append(f.LocalPath())

  if eof_files:
    return [output_api.PresubmitPromptWarning(
      'These files should end in one (and only one) newline character:',
      items=eof_files)]
  return []


def CheckChangeHasNoCrAndHasOnlyOneEol(input_api, output_api,
                                       source_file_filter=None):
  """Runs both CheckChangeHasNoCR and CheckChangeHasOnlyOneEOL in one pass.

  It is faster because it is reading the file only once.
  """
  cr_files = []
  eof_files = []
  for f in input_api.AffectedSourceFiles(source_file_filter):
    contents = input_api.ReadFile(f, 'rb')
    if '\r' in contents:
      cr_files.append(f.LocalPath())
    # Check that the file ends in one and only one newline character.
    if len(contents) > 1 and (contents[-1:] != '\n' or contents[-2:-1] == '\n'):
      eof_files.append(f.LocalPath())
  outputs = []
  if cr_files:
    outputs.append(output_api.PresubmitPromptWarning(
        'Found a CR character in these files:', items=cr_files))
  if eof_files:
    outputs.append(output_api.PresubmitPromptWarning(
      'These files should end in one (and only one) newline character:',
      items=eof_files))
  return outputs


def CheckChangeHasNoTabs(input_api, output_api, source_file_filter=None):
  """Checks that there are no tab characters in any of the text files to be
  submitted.
  """
  # In addition to the filter, make sure that makefiles are blacklisted.
  if not source_file_filter:
    # It's the default filter.
    source_file_filter = input_api.FilterSourceFile
  def filter_more(affected_file):
    return (not input_api.os_path.basename(affected_file.LocalPath()) in
                ('Makefile', 'makefile') and
            source_file_filter(affected_file))
  tabs = []
  for f, line_num, line in input_api.RightHandSideLines(filter_more):
    if '\t' in line:
      tabs.append('%s, line %s' % (f.LocalPath(), line_num))
  if tabs:
    return [output_api.PresubmitPromptWarning('Found a tab character in:',
                                              long_text='\n'.join(tabs))]
  return []


def CheckChangeTodoHasOwner(input_api, output_api, source_file_filter=None):
  """Checks that the user didn't add TODO(name) without an owner."""

  unowned_todo = input_api.re.compile('TO' + 'DO[^(]')
  for f, line_num, line in input_api.RightHandSideLines(source_file_filter):
    if unowned_todo.search(line):
      text = ('Found TO' + 'DO with no owner in %s, line %s' %
              (f.LocalPath(), line_num))
      return [output_api.PresubmitPromptWarning(text)]
  return []


def CheckChangeHasNoStrayWhitespace(input_api, output_api,
                                    source_file_filter=None):
  """Checks that there is no stray whitespace at source lines end."""
  errors = []
  for f, line_num, line in input_api.RightHandSideLines(source_file_filter):
    if line.rstrip() != line:
      errors.append('%s, line %s' % (f.LocalPath(), line_num))
  if errors:
    return [output_api.PresubmitPromptWarning(
        'Found line ending with white spaces in:',
        long_text='\n'.join(errors))]
  return []


def CheckLongLines(input_api, output_api, maxlen=80, source_file_filter=None):
  """Checks that there aren't any lines longer than maxlen characters in any of
  the text files to be submitted.
  """
  bad = []
  for f, line_num, line in input_api.RightHandSideLines(source_file_filter):
    # Allow lines with http://, https:// and #define/#pragma/#include/#if/#endif
    # to exceed the maxlen rule.
    if (len(line) > maxlen and
        not 'http://' in line and
        not 'https://' in line and
        not line.startswith('#define') and
        not line.startswith('#include') and
        not line.startswith('#import') and
        not line.startswith('#pragma') and
        not line.startswith('#if') and
        not line.startswith('#endif')):
      bad.append(
          '%s, line %s, %s chars' %
          (f.LocalPath(), line_num, len(line)))
      if len(bad) == 5:  # Just show the first 5 errors.
        break

  if bad:
    msg = 'Found lines longer than %s characters (first 5 shown).' % maxlen
    return [output_api.PresubmitPromptWarning(msg, items=bad)]
  else:
    return []


def CheckLicense(input_api, output_api, license_re, source_file_filter=None,
    accept_empty_files=True):
  """Verifies the license header.
  """
  license_re = input_api.re.compile(license_re, input_api.re.MULTILINE)
  bad_files = []
  for f in input_api.AffectedSourceFiles(source_file_filter):
    contents = input_api.ReadFile(f, 'rb')
    if accept_empty_files and not contents:
      continue
    if not license_re.search(contents):
      bad_files.append(f.LocalPath())
  if bad_files:
    if input_api.is_committing:
      res_type = output_api.PresubmitPromptWarning
    else:
      res_type = output_api.PresubmitNotifyResult
    return [res_type(
        'Found a bad license header in these files:', items=bad_files)]
  return []


def CheckChangeSvnEolStyle(input_api, output_api, source_file_filter=None):
  """Checks that the source files have svn:eol-style=LF."""
  return CheckSvnProperty(input_api, output_api,
                          'svn:eol-style', 'LF',
                          input_api.AffectedSourceFiles(source_file_filter))


def CheckSvnForCommonMimeTypes(input_api, output_api):
  """Checks that common binary file types have the correct svn:mime-type."""
  output = []
  files = input_api.AffectedFiles(include_deletes=False)
  def IsExts(x, exts):
    path = x.LocalPath()
    for extension in exts:
      if path.endswith(extension):
        return True
    return False
  def FilterFiles(extension):
    return filter(lambda x: IsExts(x, extension), files)
  def RunCheck(mime_type, files):
    output.extend(CheckSvnProperty(input_api, output_api, 'svn:mime-type',
                                   mime_type, files))
  RunCheck('application/pdf', FilterFiles(['.pdf']))
  RunCheck('image/bmp', FilterFiles(['.bmp']))
  RunCheck('image/gif', FilterFiles(['.gif']))
  RunCheck('image/png', FilterFiles(['.png']))
  RunCheck('image/jpeg', FilterFiles(['.jpg', '.jpeg', '.jpe']))
  RunCheck('image/vnd.microsoft.icon', FilterFiles(['.ico']))
  return output


def CheckSvnProperty(input_api, output_api, prop, expected, affected_files):
  """Checks that affected_files files have prop=expected."""
  if input_api.change.scm != 'svn':
    return []

  bad = filter(lambda f: f.Property(prop) != expected, affected_files)
  if bad:
    if input_api.is_committing:
      res_type = output_api.PresubmitError
    else:
      res_type = output_api.PresubmitNotifyResult
    message = 'Run the command: svn pset %s %s \\' % (prop, expected)
    return [res_type(message, items=bad)]
  return []


### Other checks

def CheckDoNotSubmit(input_api, output_api):
  return (
      CheckDoNotSubmitInDescription(input_api, output_api) +
      CheckDoNotSubmitInFiles(input_api, output_api)
      )


def CheckTreeIsOpen(input_api, output_api,
                    url=None, closed=None, json_url=None):
  """Check whether to allow commit without prompt.

  Supports two styles:
    1. Checks that an url's content doesn't match a regexp that would mean that
       the tree is closed. (old)
    2. Check the json_url to decide whether to allow commit without prompt.
  Args:
    input_api: input related apis.
    output_api: output related apis.
    url: url to use for regex based tree status.
    closed: regex to match for closed status.
    json_url: url to download json style status.
  """
  if not input_api.is_committing:
    return []
  try:
    if json_url:
      connection = input_api.urllib2.urlopen(json_url)
      status = input_api.json.loads(connection.read())
      connection.close()
      if not status['can_commit_freely']:
        short_text = 'Tree state is: ' + status['general_state']
        long_text = status['message'] + '\n' + json_url
        return [output_api.PresubmitError(short_text, long_text=long_text)]
    else:
      # TODO(bradnelson): drop this once all users are gone.
      connection = input_api.urllib2.urlopen(url)
      status = connection.read()
      connection.close()
      if input_api.re.match(closed, status):
        long_text = status + '\n' + url
        return [output_api.PresubmitError('The tree is closed.',
                                          long_text=long_text)]
  except IOError:
    pass
  return []


def RunPythonUnitTests(input_api, output_api, unit_tests):
  """Run the unit tests out of process, capture the output and use the result
  code to determine success.
  """
  # We don't want to hinder users from uploading incomplete patches.
  if input_api.is_committing:
    message_type = output_api.PresubmitError
  else:
    message_type = output_api.PresubmitNotifyResult
  outputs = []
  for unit_test in unit_tests:
    # Run the unit tests out of process. This is because some unit tests
    # stub out base libraries and don't clean up their mess. It's too easy to
    # get subtle bugs.
    cwd = None
    env = None
    unit_test_name = unit_test
    # 'python -m test.unit_test' doesn't work. We need to change to the right
    # directory instead.
    if '.' in unit_test:
      # Tests imported in submodules (subdirectories) assume that the current
      # directory is in the PYTHONPATH. Manually fix that.
      unit_test = unit_test.replace('.', '/')
      cwd = input_api.os_path.dirname(unit_test)
      unit_test = input_api.os_path.basename(unit_test)
      env = input_api.environ.copy()
      # At least on Windows, it seems '.' must explicitly be in PYTHONPATH
      backpath = [
          '.', input_api.os_path.pathsep.join(['..'] * (cwd.count('/') + 1))
        ]
      if env.get('PYTHONPATH'):
        backpath.append(env.get('PYTHONPATH'))
      env['PYTHONPATH'] = input_api.os_path.pathsep.join((backpath))
    subproc = input_api.subprocess.Popen(
        [
          input_api.python_executable,
          '-m',
          '%s' % unit_test
        ],
        cwd=cwd,
        env=env,
        stdin=input_api.subprocess.PIPE,
        stdout=input_api.subprocess.PIPE,
        stderr=input_api.subprocess.PIPE)
    stdoutdata, stderrdata = subproc.communicate()
    # Discard the output if returncode == 0
    if subproc.returncode:
      outputs.append('Test \'%s\' failed with code %d\n%s\n%s\n' % (
          unit_test_name, subproc.returncode, stdoutdata, stderrdata))
  if outputs:
    return [message_type('%d unit tests failed.' % len(outputs),
                                long_text='\n'.join(outputs))]
  return []


def _FetchAllFiles(input_api, white_list, black_list):
  """Hack to fetch all files."""
  # We cannot use AffectedFiles here because we want to test every python
  # file on each single python change. It's because a change in a python file
  # can break another unmodified file.
  # Use code similar to InputApi.FilterSourceFile()
  def Find(filepath, filters):
    for item in filters:
      if input_api.re.match(item, filepath):
        return True
    return False

  import os
  files = []
  path_len = len(input_api.PresubmitLocalPath())
  for dirpath, dirnames, filenames in os.walk(input_api.PresubmitLocalPath()):
    # Passes dirnames in black list to speed up search.
    for item in dirnames[:]:
      filepath = input_api.os_path.join(dirpath, item)[path_len + 1:]
      if Find(filepath, black_list):
        dirnames.remove(item)
    for item in filenames:
      filepath = input_api.os_path.join(dirpath, item)[path_len + 1:]
      if Find(filepath, white_list) and not Find(filepath, black_list):
        files.append(filepath)
  return files


def RunPylint(input_api, output_api, white_list=None, black_list=None):
  """Run pylint on python files.

  The default white_list enforces looking only a *.py files.
  """
  white_list = white_list or ['.*\.py$']
  black_list = black_list or input_api.DEFAULT_BLACK_LIST

  # Only trigger if there is at least one python file affected.
  src_filter = lambda x: input_api.FilterSourceFile(x, white_list, black_list)
  if not input_api.AffectedSourceFiles(src_filter):
    return []

  # On certain pylint/python version combination, running pylint throws a lot of
  # warning messages.
  import warnings
  warnings.filterwarnings('ignore', category=DeprecationWarning)
  try:
    files = _FetchAllFiles(input_api, white_list, black_list)
    if not files:
      return []
    # Now that at least one python file was modified and all the python files
    # were listed, try to run pylint.
    try:
      from pylint import lint
      result = lint.Run(sorted(files))
    except SystemExit, e:
      # pylint has the bad habit of calling sys.exit(), trap it here.
      result = e.code
    except ImportError:
      if input_api.platform == 'win32':
        return [output_api.PresubmitNotifyResult(
          'Warning: Can\'t run pylint because it is not installed. Please '
          'install manually\n'
          'Cannot do static analysis of python files.')]
      return [output_api.PresubmitError(
          'Please install pylint with "sudo apt-get install python-setuptools; '
          'sudo easy_install pylint"\n'
          'Cannot do static analysis of python files.')]
    if result:
      if input_api.is_committing:
        error_type = output_api.PresubmitError
      else:
        error_type = output_api.PresubmitPromptWarning
      return [error_type('Fix pylint errors first.')]
    return []
  finally:
    warnings.filterwarnings('default', category=DeprecationWarning)

# TODO(dpranke): Get the host_url from the input_api instead
def CheckRietveldTryJobExecution(input_api, output_api, host_url, platforms,
                                 owner):
  if not input_api.is_committing:
    return []
  if not input_api.change.issue or not input_api.change.patchset:
    return []
  url = '%s/%d/get_build_results/%d' % (
      host_url, input_api.change.issue, input_api.change.patchset)
  try:
    connection = input_api.urllib2.urlopen(url)
    # platform|status|url
    values = [item.split('|', 2) for item in connection.read().splitlines()]
    connection.close()
  except input_api.urllib2.HTTPError, e:
    if e.code == 404:
      # Fallback to no try job.
      return [output_api.PresubmitPromptWarning(
          'You should try the patch first.')]
    else:
      # Another HTTP error happened, warn the user.
      return [output_api.PresubmitPromptWarning(
          'Got %s while looking for try job status.' % str(e))]

  if not values:
    # It returned an empty list. Probably a private review.
    return []
  # Reformat as an dict of platform: [status, url]
  values = dict([[v[0], [v[1], v[2]]] for v in values if len(v) == 3])
  if not values:
    # It returned useless data.
    return [output_api.PresubmitNotifyResult('Failed to parse try job results')]

  for platform in platforms:
    values.setdefault(platform, ['not started', ''])
  message = None
  non_success = [k.upper() for k, v in values.iteritems() if v[0] != 'success']
  if 'failure' in [v[0] for v in values.itervalues()]:
    message = 'Try job failures on %s!\n' % ', '.join(non_success)
  elif non_success:
    message = ('Unfinished (or not even started) try jobs on '
                '%s.\n') % ', '.join(non_success)
  if message:
    message += (
        'Is try server wrong or broken? Please notify %s. '
        'Thanks.\n' % owner)
    return [output_api.PresubmitPromptWarning(message=message)]
  return []


def CheckBuildbotPendingBuilds(input_api, output_api, url, max_pendings,
    ignored):
  if not input_api.json:
    return [output_api.PresubmitPromptWarning(
      'Please install simplejson or upgrade to python 2.6+')]
  try:
    connection = input_api.urllib2.urlopen(url)
    raw_data = connection.read()
    connection.close()
  except IOError:
    return [output_api.PresubmitNotifyResult('%s is not accessible' % url)]

  try:
    data = input_api.json.loads(raw_data)
  except ValueError:
    return [output_api.PresubmitNotifyResult('Received malformed json while '
                                             'looking up buildbot status')]

  out = []
  for (builder_name, builder) in data.iteritems():
    if builder_name in ignored:
      continue
    if builder.get('state', '') == 'offline':
      continue
    pending_builds_len = len(builder.get('pending_builds', []))
    if pending_builds_len > max_pendings:
      out.append('%s has %d build(s) pending' %
                  (builder_name, pending_builds_len))
  if out:
    return [output_api.PresubmitPromptWarning(
        'Build(s) pending. It is suggested to wait that no more than %d '
            'builds are pending.' % max_pendings,
        long_text='\n'.join(out))]
  return []


def CheckOwners(input_api, output_api, email_regexp=None,
    source_file_filter=None):
  affected_files = set([f.LocalPath() for f in
      input_api.change.AffectedFiles(source_file_filter)])
  owners_db = input_api.owners_db
  if email_regexp:
    owners_db.email_regexp = input_api.re.compile(email_regexp)

  if input_api.is_committing and input_api.tbr:
    return [output_api.PresubmitNotifyResult(
        '--tbr was specified, skipping OWNERS check')]
  elif input_api.is_committing:
    approvers = _Approvers(input_api, owners_db.email_regexp)
    missing_files = owners_db.files_not_covered_by(affected_files, approvers)
    if missing_files:
      return [output_api.PresubmitError('Missing LGTM from an OWNER for: %s' %
              ','.join(missing_files))]
    return []
  elif input_api.change.tags.get('R'):
    return []

  suggested_reviewers = owners_db.reviewers_for(affected_files)
  return [output_api.PresubmitAddReviewers(suggested_reviewers)]


def _Approvers(input_api, email_regexp):
  if not input_api.change.issue:
    return []

  # TODO(dpranke): Should figure out if input_api.host_url is supposed to
  # be a host or a scheme+host and normalize it there.
  host = input_api.host_url
  if not host.startswith('http://') and not host.startswith('https://'):
    host = 'http://' + host
  url = '%s/api/%s?messages=true' % (host, input_api.change.issue)

  f = input_api.urllib2.urlopen(url)
  issue_props = input_api.json.load(f)
  owner = input_api.re.escape(issue_props['owner'])

  # TODO(dpranke): This mimics the logic in
  # /tools/commit-queue/verifiers/reviewer_lgtm.py
  # We should share the code and/or remove the check there where it is
  # redundant (since the commit queue also enforces the presubmit checks).
  def match_reviewer(r):
    return email_regexp.match(r) and not input_api.re.match(owner, r)

  approvers = []
  for m in issue_props.get('messages', []):
    if 'lgtm' in m['text'].lower() and match_reviewer(m['sender']):
      approvers.append(m['sender'])
  return set(approvers)
