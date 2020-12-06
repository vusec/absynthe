import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy
import ujson
import glob
import sys
import uarch

# which archs exist?
print('finding all data to plot..')
statefiles=glob.glob('state/state-test*')
if len(statefiles) < 1:
    raise Exception('no data found to plot; looking for state files in state/ directory.')
    sys.exit(1)
print('found:', statefiles)

archs=[]
arch2name = uarch.short_to_long

all_states = dict()

for statefile in statefiles:
    state=ujson.load(open(statefile))
    this_arch=state['uarch']
    print('datafile: %s uarch: %s' % (statefile,this_arch))
    archs.append(this_arch)
    if this_arch not in arch2name:
        print('WARNING: no human-friendly name for %s' % this_arch)
    if this_arch in all_states:
        raise Exception('Duplicate data for uarch %s' % this_arch)
    all_states[this_arch] = state

nsubplots=len(archs)
subplot=0

fig,axes = plt.subplots(nrows=1,ncols=nsubplots,figsize=(14,4))

assert nsubplots > 0
if nsubplots == 1:
    axes=(axes,)

for (arch,ax) in zip(archs,axes):
    subplot+=1
    print(arch)
    state=all_states[arch]
    ul=sorted(state['unreliable_set'],reverse=True)
    print('unreliable set: %s' % ul)
    numpydata=state['numpy_median_normalized_unsparse']

    print('loading aggregated data from numpy file')
    data=numpy.load(numpydata)
    print('done. shape', data.shape)

    titles=state['titles']
    tics,labels = zip(*titles)
    labels=[['%s' % (p,) for p in x] for x in labels]
    labels=['P' + '+'.join(x) for x in labels]
    print(tics,labels)
    prev=None
    ticlist=[]
    print('subplot', subplot, '/', nsubplots)
    ax.xaxis.set_label_coords(0.4,-0.08)
    for off,title in titles:
        if prev != None:
            n=float(prev+off)/2
            ticlist.append(n)
            ax.axvline(x=off-1,color='lime',linewidth=1)
            ax.axhline(y=off-1,color='lime',linewidth=1)
        prev=off
    ticlist.append(float(prev+data.shape[0])/2)
    ax.set_xticks(ticlist)
    ax.set_yticks(ticlist)
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)

#    plt.title('latency increase factor of (Y) READER instruction sequence during (X) WRITER\nvs latency of (Y) READER sequence with NOP WRITER', fontsize=11)
    ax.set_title(arch2name[arch])
    if subplot == 1:
        ax.set_ylabel('reading instruction\ngrouped by port')
    ax.set_xlabel('writer, grouped by port')
    im = ax.pcolormesh(data, vmin=1.0, vmax=3.0)
#    if subplot == nsubplots:
#        plt.colorbar()

fig.subplots_adjust(right=0.8)
cbar_ax = fig.add_axes([0.85, 0.15, 0.05, 0.7])
fig.colorbar(im, cax=cbar_ax)

pngname='covert-nuke.png'
pdfname='covert-nuke.pdf'
print('saving png %s' % pngname)
plt.savefig(pngname, bbox_inches='tight')
print('saving pdf %s' % pdfname)
plt.savefig(pdfname, bbox_inches='tight')
print('saving done')

