#!/bin/sh

cp $(git rev-parse --show-toplevel)/hooks/pre-commit $(git rev-parse --show-toplevel)/.git/hooks
