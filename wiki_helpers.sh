#!/bin/sh

for fname in Real_Deal_Trials/*
do
	#echo "$(wc -l $fname)"
	echo "$(wc -l "$fname")"
done