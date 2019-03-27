#!/bin/sh

git diff-tree --name-only -r 17.0.1..HEAD nova | tar -czf nova-lxd.patch.tar.gz -T -
