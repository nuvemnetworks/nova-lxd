#!/bin/sh

git format-patch 17.0.1..HEAD --stdout -- ':nova' > nova-lxd.patch
