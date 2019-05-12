import os
import sys
import xml.etree.ElementTree as ET
import base64
import io
import re
import struct


CONTACT_NAME = "contact_name"
UNIX_TIMESTAMP = "date"
READABLE_DATE = "readable_date"
PHONE_NUMBER = "address"
MESSAGE = "body"
TYPE = "type"
UNKNOWN = "(Unknown)"

TO_ME = "1"
FROM_ME = "2"

MMS = "mms"
SMS = "sms"

ME = "Me"

# Per "struct" module docs
UNSIGNED_SHORT = "H"

def shorts_as_utf16(short_sequence):
    if not isinstance(short_sequence, list):
        short_sequence = list(short_sequence)
    format = UNSIGNED_SHORT * (len(short_sequence) + 1)
    # 0xFEFF is a byte-order marker---however it gets encoded by pack(), the
    # UTF-16 decoder is supposed to understand it and use that interpretation
    # for the endianness of the remaining bytes.  We probably don't need it
    # here, but it can't hurt!
    bits = struct.pack(format, 0xFEFF, *short_sequence)
    return bits.decode("UTF-16")

# Numeric XML entities, e.g. "&#55357;&#56860;".
rgx1 = re.compile(r"(?:&#\d+;)+")

# Capture one of the numbers inside an entity
rgx2 = re.compile(r"&#(\d+);")

def fix_codepoints(s, raw=False):
    """Fix malformed XML entities generated by "SMS Backup & Restore".

    Note: this function may break well-formed numeric entities, so be sure that
    the input string does not mix the two.

    Input:
        s -- a string
        raw -- whether to do "raw" conversion (see "Output" below)

    Output:
        The string s, but with bad entities fixed.  If "raw" is True, the bad
        entities are replaced with their actual unicode characters.  If "raw"
        is False, the bad entities are replaced with correct XML entities.

    Details:
        SMS Backup app encodes complicated unicode characters as
          &#XXXXX;&#XXXXX;
        where the two XXX numbers are two unsigned shorts that form a UTF-16
        character.  (Makes sense---it's probably implemented in Java, which
        uses UTF-16 encoding for in-memory strings.)  Proper XML uses unicode
        codepoints (Python's ord()) for the XXX digits, so we need to do
        conversion.
    """

    matches = list(rgx1.finditer(s))
    if not matches:
        return s
    with io.StringIO() as out:
        i = 0
        for m in matches:
            out.write(s[i:m.start()])
            i = m.end()
            repl = shorts_as_utf16(int(i) for i in rgx2.findall(m.group(0)))
            if raw:
                out.write(repl)
            else:
                for c in repl:
                    out.write("&#{};".format(ord(c)))
        out.write(s[i:])
        return out.getvalue()


def format_text_data(contact, data):
  formatted_text = ""

  # sorted by unix time stamp
  keys = sorted(data, key = lambda x: x[0])

  for y in keys:
    x = y[1]

    if x[TYPE] == FROM_ME:
      formatted_text += ME + ', '
    else:
      formatted_text += contact + ', '

    formatted_text += x[READABLE_DATE] + ', '
    formatted_text += x[PHONE_NUMBER] + '\n'
    formatted_text += x[MESSAGE] + '\n\n'

  return formatted_text.encode('utf-8')


def write_files(data_by_contact, recovery_date):
  for contact in data_by_contact:
    directory = contact
    text_file = "%s/%s-texts.txt" % (contact, recovery_date)

    if not os.path.exists(directory):
      os.makedirs(directory)

    with open(text_file, 'w') as f:
      try:
        f.write(format_text_data(contact, data_by_contact[contact]))
      except:
        print contact


def write_images(encoded_images):
  for img_name in encoded_images:
    k, v = img_name
    with open(k, 'wb') as f:
      f.write(base64.decodestring(v))


def parse_sms_data(root):
  sms_data = {}
  for child in root:
    if child.tag == SMS:

      text_data = {
        READABLE_DATE: unicode(child.attrib[READABLE_DATE]),
        PHONE_NUMBER: unicode(child.attrib[PHONE_NUMBER]),
        MESSAGE: unicode(child.attrib[MESSAGE]),
        TYPE: unicode(child.attrib[TYPE]),
      }

      key = unicode(child.attrib[CONTACT_NAME])
      if key == UNKNOWN:
        # Unknown numbers all have the same contact name, so differentiate them
        # by appending the number itself.
        key = u"Unknown%s" % text_data[PHONE_NUMBER]

      # First element of tuple used for sorting texts chronologically.
      text_data_by_time = (unicode(child.attrib[UNIX_TIMESTAMP]), text_data)

      if key not in sms_data:
        sms_data[key] = []
      sms_data[key].append(text_data_by_time)
  return sms_data

class MyParser(ET.XMLParser):
  def feed (self, data):
    return super(MyParser, self).feed(fix_codepoints(data.decode('utf-8'), raw=True).encode("utf-8"))

def parse_file(file_name, recovery_date):
  tree = ET.parse(file_name, parser=MyParser())  # , parser=ET.XMLParser(target=MyParser()))
  root = tree.getroot()

  sms_data_by_contact = parse_sms_data(root)
  write_files(sms_data_by_contact, recovery_date)


def parse_images(file_name):
  encoded_images = []

  parser = ET.iterparse(file_name, events=("start", "end"))

  image_info = None
  extra_info = None
  mms_info = None
  for x in parser:
    if unicode(x[1].tag) == u'mms':
      # print x[1].attrib[CONTACT_NAME]
      mms_info = x[1]
      image_info = None
      extra_info = None
    elif unicode(x[1].tag) == u'part':
      # print x[1].attrib["ct"]
      if x[1].attrib["ct"] == "application/smil":
        extra_info = x[1]
      elif "image" in x[1].attrib["ct"]:
        image_info = x[1]
      elif x[1].attrib["ct"] == "text/plain":
        continue
      else:
        print x[1].attrib["ct"]

    if image_info is not None and extra_info is not None and mms_info is not None:
      # Here we finally have all the info about this text that we want.
      if mms_info is None:
        print extra_info.attrib
        continue
      else:
        contact = unicode(mms_info.attrib[CONTACT_NAME])
        date = unicode(mms_info.attrib[UNIX_TIMESTAMP])

      original_file_name = extra_info.attrib['text'].split("img src=\"")
      original_file_name = original_file_name[1]
      original_file_name = original_file_name.split('\"')
      original_file_name = original_file_name[0]

      output_filename = "bin/" + "%s_%s_%s" % (contact, date, original_file_name)

      encoded_image = unicode(image_info.attrib['data'])

      image_data = (output_filename, encoded_image)
      encoded_images.append(image_data)

      image_info = None
      mms_info = None
      extra_info = None
  write_images(encoded_images)


def parse_arguments(argv):
  # no error checking
  input_file = argv[1]
  recovery_date = input_file.split('-')[1][:8]
  return input_file, recovery_date


if __name__ == "__main__":
  file_name, recovery_date = parse_arguments(sys.argv)
  if True:
    parse_file(file_name, recovery_date)
  else:
    parse_images(file_name)
