#!/bin/sh

git format-patch 17.0.1..HEAD --no-prefix --stdout -- ':nova' > nova-lxd.patch
