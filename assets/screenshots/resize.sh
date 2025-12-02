#!/bin/bash

mkdir -p 480x800
for img in *.png; do
    convert "$img" -resize 480x800\! "480x800/$img"
done
