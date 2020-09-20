#!/bin/bash

source_dir="docs_source"
output_dir="docs"

sphinx-build -b html $source_dir $output_dir

cd $source_dir || exit
sphinx-build -b html . ../$output_dir