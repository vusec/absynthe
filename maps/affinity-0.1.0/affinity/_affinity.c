/* Enfold Enterprise Server */
/* Copyright(C), 2004-5, Enfold Systems, LLC - ALL RIGHTS RESERVED */

/* Enfold Systems, LLC */
/* 4617 Montrose Blvd., Suite C215 */
/* Houston, Texas 77006 USA */
/* p. +1 713.942.2377 | f. +1 832.201.8856 */
/* www.enfoldsystems.com */
/* info@enfoldsystems.com */

/* Inspired by:  */
/* http://www.linuxjournal.com/article/6799 */

#include "Python.h"
#ifndef _GNU_SOURCE
#define _GNU_SOURCE             /* See feature_test_macros(7) */
#endif
#include <sched.h>

PyDoc_STRVAR(_affinity__doc__, "Linux Processor Affinity\n");

static PyObject *
mask_to_python(pid_t pid)
{
  cpu_set_t cur_mask;
  unsigned int len = sizeof(cur_mask);

  if (sched_getaffinity(pid, len,
                        (cpu_set_t *)&cur_mask) < 0) {
    PyErr_SetFromErrno(PyExc_ValueError);
    return NULL;
  }

  PyObject *curval = Py_BuildValue("l", 0);
  PyObject *one = Py_BuildValue("l", 1);

  int i;

  for(i = 0; i < CPU_SETSIZE; i++) {
      if(!CPU_ISSET(i, &cur_mask))
          continue;
      PyObject *cpuval = Py_BuildValue("l", i);
      PyObject *nextval_add = PyNumber_Lshift(one, cpuval);
      PyObject *nextval = PyNumber_Add(curval, nextval_add);
      Py_DECREF(cpuval);
      Py_DECREF(nextval_add);
      Py_DECREF(curval);
      curval = nextval;

//      fprintf(stderr, "getting: cpu set: %d\n", i);
  }

  Py_DECREF(one);

  return curval;
}

static PyObject *
get_process_affinity_mask(PyObject *self, PyObject *args)
{
  pid_t pid;

  if (!PyArg_ParseTuple(args, "i:get_process_affinity_mask", &pid))
    return NULL;

  return mask_to_python(pid);
}

static PyObject *
set_process_affinity_mask(PyObject *self, PyObject *args)
{
  cpu_set_t new_mask;
  unsigned int len = sizeof(new_mask);
  pid_t pid;

  PyObject *maskarg;

  if (!PyArg_ParseTuple(args, "iO", &pid, &maskarg))
    return NULL;

  if(!PyNumber_Check(maskarg))
      return NULL;

  PyObject *oldmask = mask_to_python(pid);
  PyObject *one = Py_BuildValue("l", 1);

  CPU_ZERO(&new_mask);

  int i;
  for(i = 0; i < CPU_SETSIZE; i++) {
      PyObject *cpuval = Py_BuildValue("l", i);
      PyObject *cpuval_shifted = PyNumber_Rshift(maskarg, cpuval);
      PyObject *anded = PyNumber_And(cpuval_shifted, one);
      Py_DECREF(cpuval);
      Py_DECREF(cpuval_shifted);
      long v = PyLong_AsLong(anded);
      Py_DECREF(anded);
      if(v == 0) continue;
      assert(v == 1);
      CPU_SET(i, &new_mask);
//      fprintf(stderr, "setting: cpu set: %d\n", i);
  }

  Py_DECREF(one);

  if (sched_setaffinity(pid, len, (cpu_set_t *)&new_mask)) {
    PyErr_SetFromErrno(PyExc_ValueError);
    return NULL;
  }

  return oldmask;
}

static PyMethodDef methods[] = {
  {"get_process_affinity_mask", get_process_affinity_mask, METH_VARARGS,
    "get_process_affinity_mask(pid) ->\n\
Get the process affinity mask of 'pid'.\n\n\
You can get the affinity mask of any process running\n\
in the system, even if you are not the process owner."},
  {"set_process_affinity_mask", set_process_affinity_mask, METH_VARARGS,
    "set_process_affinity_mask(pid, affinity_mask) ->\n\
Set the process affinity mask of 'pid' to 'affinity_mask'\n\
and return the previous affinity mask.\n\n\
If the PID is set to zero, the PID of the current task is used.\n\n\
Note: you must be 'root' or the owner of 'pid' in\n\
order to be able to call this."},
  {NULL, NULL},
};

PyMODINIT_FUNC
PyInit__affinity(void)
{
    static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT,
        "_affinity",         /* m_name */
        _affinity__doc__,    /* m_doc */
        -1,                  /* m_size */
        methods,             /* m_methods */
        NULL,                /* m_reload */
        NULL,                /* m_traverse */
        NULL,                /* m_clear */
        NULL,                /* m_free */
    };
    PyObject* m = PyModule_Create(&moduledef);
    return m;
}

