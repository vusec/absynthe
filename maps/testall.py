import subprocess
import pickle
import glob
import os
import csv
import random
import sys
import ujson
import cpus
import numpy
import tqdm
from io import StringIO
from scipy import stats
import xml.etree.ElementTree as ET
import affinity

if __name__ != "__main__":
    raise Exception('not intended for import but for execution')

def getconfig(exe):
    """
    We invoke the test executable to get some configuration from it so we
    don't have to hard-code it between python and C.
    The executable returns it in a python dict which we eval() to get it.
    'writerfailstring' is the string the executable will produce when its
    sibling test program has crashed. 'available' is a list of numbers
    corresponding to available instructions (workloads).

    we need a high recursion limit to eval() the output.
    """
    process_output = subprocess.check_output([exe, "available"])
    process_output = process_output.decode('ascii')
    try:
        lim = sys.getrecursionlimit()
        if lim < 35000:
            sys.setrecursionlimit(35000)
        print('doing eval with recursion limit %d' % sys.getrecursionlimit())
        configdict = eval(process_output)
    except RecursionError:
        print('parsing of binary output failed with recursionerror.')
        sys.exit(1)
    return configdict['writerfailstring'], configdict['available']

def get_work_cpus():
        """
        Work cpus are the processors (logical processors) that are used to execute the
        cross-thread measurement worklads. We allow all the LP's in the system to do
        this, except for the LP's for one physical core. These are the 'master cpus,'
        reserved for the parent process, the python interpreter. We use the affinity
        module to pin the python interpreter to these LP's. We return the rest of the
        LP's.
        """
        cpulist=cpus.corelist(True)
        master_cpus = cpulist.pop()
        mask=0
        for c in master_cpus:
                mask |= 1 << c
        affinity.set_process_affinity_mask(0,mask)
        print('master cpus (for python):', master_cpus,file=sys.stderr)
        print('worker cpus:', cpulist,file=sys.stderr)
        return cpulist

def usage():
    print('Usage:  %s <generated-binary> testall <number-of-instrs>' % sys.argv[0])
    print('        %s plot' % sys.argv[0])
    sys.exit(1)

def acquire(exe, uarch, num_measurements, with_progressbar, n_instructions=None):
    disable_progressbar = not with_progressbar
    writerfailstring, baseline_list=getconfig(exe)

    if n_instructions != None:
        print('truncating baseline list of %d to %d' % (len(baseline_list),n_instructions), file=sys.stderr)
        baseline_list = sorted(baseline_list)[0:n_instructions]
    else:
        n_instructions=len(baseline_list)

    state_json_fn='state/state-test-n%d-i%d-uarch-%s.json' % (num_measurements, n_instructions, uarch)
    if os.path.exists(state_json_fn) and os.path.getsize(state_json_fn) > 0:
        state=ujson.load(open(state_json_fn))
        unreliable_set=set(state['unreliable_set'])
        pickle_files=state['pickle_files']
        assert baseline_list == state['baseline_list']
        assert uarch == state['uarch']
        assert num_measurements == state['iterations']
        assert n_instructions == state['instructions']
    else:
        state=dict()
        unreliable_set=set()
        pickle_files=dict()

    work_cpus = get_work_cpus()
    work_threads=work_cpus[0]
    if len(work_threads) < 2:
        raise Exception('first physical core seemingly does not have more than one thread - but I really need two threads for this')
    trial_cpu1, trial_cpu2 = work_threads[0:2]

    warmup_number=1000
    reliable_list = list(set(baseline_list) - unreliable_set)
    assert 0 not in reliable_list
    writerlist = [0] + reliable_list
    for write in tqdm.tqdm(writerlist, disable=disable_progressbar):
        with open(state_json_fn, 'w') as fp:
               state['unreliable_set'] = list(unreliable_set)
               state['baseline_list'] = baseline_list
               state['iterations'] = num_measurements
               state['instructions'] = n_instructions
               state['uarch'] = uarch
               state['pickle_files'] = pickle_files
               ujson.dump(state, fp)
        fn_summary='ccgrid/write%d-n%d-i%d-%s-summary.pickle' % (write, num_measurements, n_instructions, uarch)
        data_updated=False
        alldata_summary=dict()
        if os.path.exists(fn_summary):
            with open(fn_summary, 'rb') as fp_summary:
                try:
                    alldata_summary=pickle.load(fp_summary)
                except:
                    alldata_summary=dict()
                alldata_summary={int(x): alldata_summary[x] for x in alldata_summary}
            if disable_progressbar:
                print('loaded summary for writer %d: %s' % (write, fn_summary))
            if len(alldata_summary) > 0:
                pickle_files[fn_summary] = {'writer': write }
                continue
        acquire_set = set(baseline_list) - unreliable_set
        have_set_summary = set(alldata_summary)
        if acquire_set <= have_set_summary:
            if disable_progressbar:
             print(write, ': all entries already there in summary')
            continue
        writerfail=False
        retries = 0
        alldata=dict()
        have_set_data = set(alldata)
        if disable_progressbar:
            print(write, ':', 'readers already acquired:', len(have_set_summary), 'data:', len(have_set_data), 'missing values from summary:', len(acquire_set - have_set_summary), 'missing values from data:', len(acquire_set - have_set_data))
        while retries < 50:
            retries+=1
            have_set = set([int(x) for x in alldata])
            acquire_list = list(set(baseline_list) - unreliable_set - have_set)
            if len(acquire_list) == 0:
                if disable_progressbar:
                    print('no need for acquire')
                break
            random.shuffle(acquire_list)
            if disable_progressbar:
                print('acquiring data for writer no. %d and %d readers' %(len(acquire_list), write))
            # Kill any lingering processes that didn't exit for some reason
            # This shouldn't happen but if it does would totally mess up the experiments.
            invoke_args=[ killall, '-KILL', os.path.basename(exe)]
            if disable_progressbar:
                print('invoking %s' % invoke_args)
            subprocess.call(invoke_args, stdout=devnull, stderr=devnull)
            invoke_args = [ exe,str(trial_cpu1), str(trial_cpu2), str(write), str(num_measurements), str(warmup_number)] + [str(x) for x in acquire_list]
            p=subprocess.Popen(invoke_args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out=None
            err=None
            try:
                    out,err = p.communicate(timeout=4)
            except subprocess.TimeoutExpired:
                    if disable_progressbar:
                        print('timeout')
                    subprocess.call([ killall, '-9', os.path.basename(exe)], stdout=devnull, stderr=devnull)
                    out,err = p.communicate()
            out = out.decode('ascii')
            err = err.decode('ascii')
            if disable_progressbar:
                print('acquiring done', len(acquire_list))
            if writerfailstring in out:
                print('writer failed:', write, 'output bytes:', len(out), 'err:', len(err), 'unreliable set:', len(unreliable_set))
                writerfail=True
                break
            f = StringIO(out)
            if p.returncode != 0:
                print('WARNING: exitcode:', p.returncode)
                print('err out:', err)
#            print('parsing output:', out)
            reader = csv.reader(f, delimiter=',')
            for fields in reader:
                if len(fields) == 2 + num_measurements:
                        n = int(fields[0])
                        assert n != 0
                        assert n in baseline_list
                        assert n in acquire_list
                        assert n not in unreliable_set
                        acquire_list.remove(n)
                        assert n not in alldata
                        alldata[n] = fields
                        data_updated=True
                else:
                    if len(fields) > 0:
                        print('partial capture')
                        try:
                            n = int(fields[0])
                        except:
                            print('first field is a bad int. fields are:', fields, file=sys.stderr)
                            sys.exit(1)
                    else:
                        raise Exception('do not understand output', fields)
                    assert n in baseline_list
                    assert n in acquire_list
                    assert n not in unreliable_set
                    assert n not in alldata
                    unreliable_set.add(n)
                    print('reader failed:', n, 'bad data, fields:', len(fields), 'fields for writer', write, 'unreliable set:', len(unreliable_set))
            if writerfail:
                print('gave up on this writer')
                break
            if len(acquire_list) == 0:
                if disable_progressbar:
                    print('acquired all for writer', write)
                break
            print('did not acquire all for writer %d - remaining %d - retrying' % (write,len(acquire_list)), end=' ')
        acquire_set = set(baseline_list) - unreliable_set
        if data_updated:
          missing_elements = acquire_set - set(list(alldata))
          if len(missing_elements) > 0:
              print('wanted:', len(acquire_set), 'got:', len(alldata), 'missing elements:', acquire_set - set(list(alldata)))
          assert acquire_set <= set(list(alldata))
        if set(alldata_summary) != set(alldata):
          if disable_progressbar:
             print('generating summary')
          assert acquire_set <= set(list(alldata))
          for x in alldata:
                arr = numpy.asarray([int(v) for v in alldata[x][2:]])
                assert arr.shape[0] == num_measurements
                alldata_summary[x] = [numpy.min(arr), numpy.max(arr), numpy.mean(arr), numpy.median(arr)]
          assert acquire_set <= set(list(alldata_summary))
          if disable_progressbar:
              print('writing summary len ', len(alldata_summary), len(alldata))
          with open(fn_summary, 'wb') as fp:
            pickle.dump(alldata_summary, fp)
          pickle_files[fn_summary] = {'writer': write }
          if disable_progressbar:
            print('writing done')

parsed_root=None

def xml_getroot():
    global parsed_root
    if parsed_root == None:
        xmlfile='instructions.xml'
        print('parsing %s' % xmlfile)
        parsed_root = ET.parse(xmlfile)
        print('parsing done')
    return parsed_root

def unsparse_list_sorted(valid_list,arch):
    valid_set=set(valid_list)
    root = xml_getroot()
    lineno = 0
    instr_ports_map=dict()
    ports_instr_map = dict()
    for instrNode in root.iter('instruction'):
        lineno += 1
        if lineno not in valid_set:
            continue
        archfound=False
        asm = instrNode.attrib['asm']
        for archNode in instrNode.iter('architecture'):
          if archNode.attrib['name'] == arch:
              archfound=True
              break
        if not archfound:
            continue
        assert archNode.attrib['name'] == arch
        measurements = list(archNode.iter('measurement'))
        assert len(measurements) < 2
        instr_ports_map[lineno] = ''
        if len(measurements) == 0:
            print('hey weird, len', len(measurements), 'for asm', asm, 'for ports')
            continue
        assert len(measurements) == 1
        measurement = measurements[0]
        if 'ports' not in measurement.attrib:
            continue
        ports=measurement.attrib['ports']
        portset=''
        for addends in ports.split('+'):
            muls=addends.split('*')
            assert len(muls) <= 2
            if len(muls) == 1:
                portset+=muls[0]
            else:
                assert len(muls) == 2
                portset+=muls[1]
        porttuple = tuple(sorted(list(set(portset) - set('FPp'))))
        instr_ports_map[lineno] = porttuple
        if not porttuple in ports_instr_map:
            ports_instr_map[porttuple] = set()
        ports_instr_map[porttuple].add(lineno)
    unsparse_list=[]
    title_list=[]
    tuplist=[]
    tuplist = ["0", "1", "5", "01"] # , "05", "15"]
    if arch == 'ZEN+':
        tuplist =  ["0", "2", "3", "03"]
    elif arch == 'BDW':
        tuplist = ["0", "1", "5", "01"] # , "05", "15"]
    elif arch == 'KBL':
        tuplist = ["0156", "06", "01", "5", "0123", "0123456"]
    else:
        print('WARNING: you probably want to customize the list of\nexecution ports to filter and group by, using default',file=sys.stderr)
    print('valid port sets for %s:' % arch)
    for p in sorted(ports_instr_map, key=lambda x: len(ports_instr_map[x]), reverse=True):
        print('   port set %-20s, matching instructions %d' % (p, len(ports_instr_map[p])))
    for tup in tuplist:
        if tuple(tup) in ports_instr_map:
            title_list+=[(len(unsparse_list),tup)]
            unsparse_list += ports_instr_map[tuple(tup)]
            print('added tuple', tup)
        else:
            print('WARNING: skipping ports tuple', tup, 'because there are no instructions for %s matching it' % arch)
    if len(title_list) < 1:
        raise Exception('not enough ports')
    return title_list, {unsparse_list[x]: x for x in range(len(unsparse_list)) }


def aggregate(with_progressbar):
        disable_progressbar = not with_progressbar
        for statefile in sorted(glob.glob('state/state-test-*json')):
            state=ujson.load(open(statefile))
            uarch=state['uarch']
            assert len(uarch) == 3 or len(uarch) == 4
            baseline_list=state['baseline_list']
            num_measurements = state['iterations']
            n_instructions = state['instructions']
            print('baseline list len %s: %d. iterations: %d instructions: %d.' % (uarch,
                        len(baseline_list), num_measurements, n_instructions))
            assert baseline_list==sorted(baseline_list)
            assert 0 not in baseline_list
            assert len(set(baseline_list)) == len(baseline_list)
            available_writers=set()
            alldata_by_writers=dict()
            n=0
            all_writers=set()
            all_readers=None
            all_files = list(state['pickle_files'])
            print('uarch:', uarch, 'summaries:', len(all_files), file=sys.stderr)
            if len(all_files) < 1:
                print('no data found', file=sys.stderr)
                raise Exception('no data files found in ccgrid/ for uarch %s' % uarch)
            print('reading source data')
            for fn in tqdm.tqdm(sorted(all_files), disable=disable_progressbar):
                n+=1
                writeno=state['pickle_files'][fn]['writer']
                all_writers.add(writeno)
                if writeno != 0:
                    assert writeno in baseline_list
                else:
                    assert writeno not in baseline_list
                assert writeno not in alldata_by_writers
                alldata_by_writers[writeno] = dict()
                with open(fn, 'rb') as fp:
                    data=pickle.load(fp)
                    these_readers=list([int(x) for x in data])
                    if all_readers == None:
                        all_readers = set(these_readers)
                    else:
                        all_readers &= set(these_readers)
                    if disable_progressbar:
                        print(n, '/', len(all_files), ':', fn,writeno, 'valid reader instrs:', len(all_readers), 'valid r+w instrs:', len(all_readers & all_writers))
                    for readno in data:
                        # alldata_summary[x] = [numpy.min(arr), numpy.max(arr), numpy.mean(arr), numpy.median(arr), stats.mode(arr)]
                        #print readno, data[readno]
                        lat_measurements=[float(x) for x in data[readno][0:4]]
                        readno=int(readno)
                        assert readno != 0
                        raw_v = lat_measurements[2] # mean
                        alldata_by_writers[writeno][readno] = raw_v
                        assert 0 in alldata_by_writers # NOP writer available?
                        assert readno in alldata_by_writers[0] # NOP writer available for this reader?
            valid_list_orig = sorted(list(all_readers & all_writers))
            max_n = max(valid_list_orig)
            print('all readers:', len(all_readers), 'all writers:', len(all_writers), 'valid both:', len(valid_list_orig), 'max n:', max_n)
            full_nxn_medians = numpy.zeros((max_n+1,max_n+1)) #reader, writer
            print('len valid_list:', len(valid_list_orig))
            title_list, unsparse = unsparse_list_sorted(valid_list_orig, uarch)
            valid_list = list(unsparse)
            assert 0 not in unsparse
            assert len(unsparse) == len(valid_list)
            n=len(unsparse)
            assert len(set(unsparse)) == len(unsparse) # check uniqueness
            nxn_medians = numpy.zeros((n,n)) #reader, writer
            assert 0 in alldata_by_writers
            w=0
            if disable_progressbar:
                print('writing ', end=' ')
            for writeno in tqdm.tqdm(valid_list_orig, disable=disable_progressbar):
                w+=1
                if disable_progressbar:
                    print(w,end=' ')
                assert writeno != 0
                for readno in valid_list_orig:
                        assert readno != 0
                        norm_v=float(alldata_by_writers[writeno][readno])/float(alldata_by_writers[0][readno])
                        if writeno in valid_list and readno in valid_list:
                            assert readno in unsparse
                            assert writeno in unsparse
                            readno_unsparse = unsparse[readno]
                            writeno_unsparse = unsparse[writeno]
                            nxn_medians[readno_unsparse][writeno_unsparse] = norm_v
                        full_nxn_medians[readno][writeno] = norm_v
            print('saving numpy')
            state['numpy_median_normalized_unsparse'] = 'ccgrid-aggregated/%s_unsparse_nxn_median_normalized_n%d_i%d.npy' % (uarch,num_measurements,n_instructions)
            state['numpy_median_normalized_full'] = 'ccgrid-aggregated/%s_full_nxn_median_normalized_n%d_i%d.npy' % (uarch,num_measurements,n_instructions)
            numpy.save(state['numpy_median_normalized_unsparse'], nxn_medians)
            numpy.save(state['numpy_median_normalized_full'], full_nxn_medians)
            state['titles'] = title_list
            print('saving json state')
            tmpfn=statefile+'.tmp'
            with open(tmpfn, 'w') as tmpfp:
                ujson.dump(state, tmpfp)
            os.rename(tmpfn, statefile)
            print('saving done')

if __name__ == "__main__":
    global killall, measurements, warmup, devnull
    killall='/usr/bin/killall'
    measurements=5
    warmup=5
    devnull=open('/dev/null', 'w')
    if not os.path.exists(killall):
        raise Exception('need killall binary')
    if len(sys.argv) < 2:
        usage()
    if 'progressbar' in sys.argv:
        progressbar=True
    else:
        progressbar=False
    if len(sys.argv) >= 5 and sys.argv[2] == 'testall':
        exe=sys.argv[1]
        uarch=sys.argv[3]
        num_measurements=int(sys.argv[4])
        acquire(exe, uarch, num_measurements, progressbar)
    if sys.argv[1] == 'aggregate':
        aggregate(progressbar)
