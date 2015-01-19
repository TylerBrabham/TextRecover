import os
import sys.argv
import xml.etree.ElementTree as ET


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


def format_text_data(contact, data):
  formatted_text = ""

  # sorted by unix time stamp
  keys = sorted(data, key = lambda x: x[0])

  for y in keys:
    x = y[1]

    if x[TYPE] == FROM_ME:
      formatted_text += MY_NAME + ', '
    else:
      formatted_text += contact + ', '

    formatted_text += x[READABLE_DATE] + ', '
    formatted_text += x[PHONE_NUMBER] + '\n'
    formatted_text += x[MESSAGE] + '\n\n'

  return formatted_text.encode('utf-8')


def write_files(data_by_contact):
  for contact in data_by_contact:
    directory = contact
    text_file = "%s/texts.txt" % contact

    if not os.path.exists(directory):
      os.makedirs(directory)

    with open(text_file, 'w') as f:
      try:
        f.write(format_text_data(contact, data_by_contact[contact]))
      except:
        print contact


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


def parse_file():
  tree = ET.parse('sms-20150118162317.xml')
  root = tree.getroot()

  sms_data_by_contact = parse_sms_data(root)
  write_files(sms_data_by_contact)


def parse_arguments(argv):
  pass


if __name__ == "__main__":
  user_name, user_number = parse_arguments(sys.argv)
  parse_file(user_name, user_number)