#!/usr/bin/env python3

import os
import yaml


languages = ["en","de"]
dat = []


for lang in languages:
	with open(os.path.join("..","i18n","i18n."+lang+".yml"),'r') as fs:
		try:
			dat.append(yaml.safe_load(fs)[lang])
		except yaml.YAMLError as exc:
			print(exc)
			exit(-1)


lengths = [ len(x) for x in dat ]

l = lengths[0]

# Check that every language has the same number of entries!
for i in range(len(languages)):
	if len(dat[i]) != l:
		print(f"Language {languages[i]} has to less entries!")
		exit(-1)

# Check if all keys are present in every language
list(dat[0].keys())
for i in range(len(languages)):
	if list(dat[0].keys()) != list(dat[i].keys()):
		print(f"Keys are different for language {languages[0]} and {languages[i]}")
		exit(-1)

print("Everything seems fine!")


print(l)