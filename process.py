#!/usr/bin/env python3

import sys
import errno
import os
import re
import requests
import glob
import img2pdf
from bs4 import BeautifulSoup

def download(url: str, dest_folder: str, filename: str):
  if not os.path.exists(dest_folder):
    os.makedirs(dest_folder)  # create folder if it does not exist

  file_path = os.path.join(dest_folder, filename)

  r = requests.get(url, stream=True)
  if r.ok:
    with open(file_path, 'wb') as f:
      for chunk in r.iter_content(chunk_size=1024 * 8):
        if chunk:
          f.write(chunk)
          f.flush()
          os.fsync(f.fileno())
  else:  # HTTP status code 4XX/5XX
    print("Download failed: status code {}\n{}".format(r.status_code, r.text))

def mkdir_p(path):
    try:
      os.makedirs(path)
    except OSError:
      pass

def flush_files():
  files = glob.glob("/tmp/comicDownload/*")
  for f in files:
    os.remove(f)

def process_issue(content,out_directory,url):

  print("Processing '" + url +"'")

  soup = BeautifulSoup(content,features="html.parser")
  issue_title = soup.find('div',{'class': 'heading'}).find('h3').text

  content = content.splitlines()
  content = filter(lambda i: i.strip().startswith("lstImages.push"), content)
  content = map(lambda i: i.strip()[16:-3], content)

  # Download images
  for i, image in enumerate(content):
    i_formatted = format(i+1, '04d')
    download(image, dest_folder="/tmp/comicDownload/", filename=str(i_formatted) + ".jpg")

  filenames = [f for f in glob.iglob(f'/tmp/comicDownload/*.jpg')]
  filenames = sorted(filenames, key=lambda x:float(re.findall("(\d+)",x)[0]))

  # Create pdf
  out_file = os.path.join(out_directory, issue_title) + ".pdf"
  with open(out_file,"wb") as f:
    f.write(img2pdf.convert(filenames))

  print("Warning - Saved comic to '" + out_file + "'")

  # Flush files in tmp folder
  flush_files()


def iterate_issues(soup,out_directory):

  # Retrieve issue links from series page
  issues = soup.find("ul", class_="list").findAll("a");

  # Iterate over issues and process individually
  for issue in issues:
    content = requests.get("https://readcomiconline.to" + issue['href'] + "&readType=1")
    url = "https://readcomiconline.to" + issue['href']
    process_issue(content.text,out_directory,url)

def identify_url(url):

  if not "readcomiconline.to" in url:
    return -1;

  # Return if series (1) or single issue (0)
  url = url.replace("https://","");
  if url.count("/") == 2:
    return 1;
  else:
    return 0;

# Usage information
if len(sys.argv) < 3:
  print("USAGE: {} [URL] [OUTPUT DIRECTORY]".format(sys.argv[0]))
  sys.exit(1);

url=sys.argv[1]
out_directory=sys.argv[2]

# Check URL
url_type = identify_url(url)

if url_type == -1:
  print("Error - URL isn't supported")
  sys.exit(1);

content = requests.get(url)
soup = BeautifulSoup(content.text,features="html.parser")

# Make folders
mkdir_p("/tmp/comicDownload/")
mkdir_p(out_directory)

# Process URL
if url_type == 1:
  iterate_issues(soup,out_directory)
elif url_type == 0:
  process_issue(content.text,out_directory,url)
