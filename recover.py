import os
import sys
import xml.etree.ElementTree as ET
import base64


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


def parse_file(file_name, recovery_date):
  tree = ET.parse(file_name)
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
  # parse_file(file_name, recovery_date)

  parse_images(file_name)