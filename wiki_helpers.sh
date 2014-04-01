#!/bin/sh

for fname in Data_Collection/*
do
	#echo "$(wc -l $fname)"
	echo "$(wc -l "$fname")"
done