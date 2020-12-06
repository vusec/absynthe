/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#pragma once

#define _GOT_PROFILE_H 1

#include <stdint.h>
#include <stdlib.h>

#include "macros.h"

#if defined(__x86_64__)
#include <x86-64/profile.h>
#elif defined(__aarch64__)
#include <arm64/profile.h>
#elif defined(__arm__)
#include <arm/profile.h>
#else
#error unsupported architecture.
#endif

int init_profiler(int cpuno);
uint64_t profile_access(volatile char *p);

