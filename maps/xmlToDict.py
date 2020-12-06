#!/usr/bin/python
import xml.etree.ElementTree as ET
import sys
import pickle

def main():
   root = ET.parse('instructions.xml')

   instr2asm=dict()

   readlabels=dict()
   writelabels=dict()
   readstringlabels=dict()
   writestringlabels=dict()

   cplmiss=0
   extensionmiss=0
   hit=0

   privileged=["CLI", "STI", "IRET", "IRETW", "IRETD", "IRETQ", "LGDT"]

   lineno = 0
   for instrNode in root.iter('instruction'):
      lineno += 1
      # Future instruction set extensions
      if instrNode.attrib['extension'] in ['CLDEMOTE', 'MOVDIR', 'PCONFIG', 'WAITPKG', 'WBNOINVD']:
         extensionmiss+=1
         continue

      cpl=instrNode.attrib['cpl']
      if cpl == 'None':
          cplmiss+=1
          continue
      if int(instrNode.attrib['cpl']) < 3:
          cplmiss+=1
          continue
      if instrNode.attrib['category'] == 'IOSTRINGOP' or instrNode.attrib['category'] == 'IO':
          cplmiss+=1
          continue

      asm = instrNode.attrib['asm']
      if asm == 'FNOP':
          print '# FNOP is', lineno

      if asm in privileged:
          cplmiss+=1
          continue

      first = True
      op_types = ''
      unusable_regs = ['ECX', 'RCX', 'R9', 'R9d', 'R11', 'R11d' ]
      hit+=1
      for operandNode in instrNode.iter('operand'):
         operandIdx = int(operandNode.attrib['idx'])

         if operandNode.attrib.get('suppressed', '0') == '1':
            continue;

         if not first and not operandNode.attrib.get('opmask', '') == '1':
            asm += ', '
         else:
            asm += ' '
            first = False

         if operandNode.attrib['type'] == 'reg':
            registers = operandNode.text.split(',')
            assert len(registers) > 0
            if 'w' in operandNode.attrib and int(operandNode.attrib['w']) > 0:
              for r in unusable_regs:
                if r in registers:
                    registers.remove(r)
            if len(registers) == 0:
                print 'fail: %s', asm
            assert len(registers) > 0
            scale = (4 if 'MM' in operandNode.text else 1)
            ix = min(operandIdx*scale, len(registers)-1)
            assert ix >= 0
            assert ix < len(registers)
            register = registers[ix]
            if register == 'RCX' and 'R8' in registers:
                register = 'R8'
            if not operandNode.attrib.get('opmask', '') == '1':
               asm += register
            else:
               asm += '{' + register + '}'
               if instrNode.attrib.get('zeroing', '') == '1':
                  asm += '{z}'
         elif operandNode.attrib['type'] == 'mem':
            memoryPrefix = operandNode.attrib.get('memory-prefix', '')
            if memoryPrefix:
               asm += memoryPrefix + ' '

            if operandNode.attrib.get('VSIB', '0') != '0':
               asm += '[' + operandNode.attrib.get('VSIB') + '0]'
            else:
               asm += '[RSI]'

            memorySuffix = operandNode.attrib.get('memory-suffix', '')
            if memorySuffix:
               asm += ' ' + memorySuffix
         elif operandNode.attrib['type'] == 'agen':
            agen = instrNode.attrib['agen']
            address = []

            if 'R' in agen: address.append('RIP')
            if 'B' in agen: address.append('RSI')
            if 'I' in agen: address.append('2*RBX')
            if 'D' in agen: address.append('8')

            asm += ' [' + '+'.join(address) + ']'
         elif operandNode.attrib['type'] == 'imm':
            if instrNode.attrib.get('roundc', '') == '1':
               asm += '{rn-sae}, '
            elif instrNode.attrib.get('sae', '') == '1':
               asm += '{sae}, '
            width = int(operandNode.attrib['width'])
            if operandNode.attrib.get('implicit', '') == '1':
               imm = operandNode.text
            else:
               imm = (1 << (width-8)) + 1
               imm = 0
            asm += str(imm)
         elif operandNode.attrib['type'] == 'relbr':
             if 'CALL' in asm:
                 asm = asm + ' genericret'
             else:
                 asm = asm + '1f ; 1: nop; '
         else:
            raise Exception('say what')
         op_types += operandNode.attrib['type'] + ' '

      if not 'sae' in asm:
         if instrNode.attrib.get('roundc', '') == '1':
            asm += ', {rn-sae}'
         elif instrNode.attrib.get('sae', '') == '1':
            asm += ', {sae}'
      instr2asm[lineno]=asm

   sys.stderr.write('cpl miss: %d extension miss: %s hit: %d\n' % (cplmiss, extensionmiss, hit))
   pickle.dump(instr2asm,open('instr2asm.pickle','w'))

def generate_table(tablename, table):
   print '.section .data'
   print '.global %s, %s_number' % (tablename,tablename)
   print '.align 8'
   print '%s:' % (tablename,)
   elems=max(table)+1
   for r in [table[x] if x in table else 0 for x in range(elems)]:
       print '.quad', r
   print '%s_number: .quad %d' % (tablename,elems)
   print '.section .text'

def generatecode(lineno, line, readmode):
    # RDTSCP: EDX:EAX
    if readmode:
        labelname = 'readinstr%s' % lineno
        n=10
    else:
        labelname = 'writeinstr%s' % lineno
        n=200
    asmlabelname = 'asmstr%s' % labelname
    print '.align 8'
    print '%s:' % labelname
    print 'PUSH RBP'
    print 'PUSH RBX'
    print 'PUSH R12'
    print 'PUSH R13'
    print 'PUSH R14'
    print 'PUSH R15'
    print 'MOVQ RAX, offset keepsp'
    print 'MOVQ [RAX], RSP'
    print 'MOVQ RCX, 10' # small number of repeats for REP prefix
    print 'MOVQ RSP, offset lotsofstackspace_highaddr'
    print 'MOVQ R8, offset 3f' # use R8 to push lotsofspace stack
    print 'PUSHQ R8' # return address to end of instruction seqeunce
    print 'MOVQ R8, offset genericret' # address to CALL to
    if 'XSAVE' in line:
        print 'MOVQ RSI, offset lotsofstackspace_lowaddr_addr' # address to CALL indirectly to
    else:
        print 'MOVQ RSI, offset genericretaddr' # address to CALL indirectly to
    print 'CLD'
    if 'POPFW' in line:
        print '.rept %d' % n
        print 'PUSHFW'
        print '.endr'
    if 'POPFL' in line:
        print '.rept %d' % n
        print 'PUSHFL'
        print '.endr'
    if 'POPFQ' in line:
        print '.rept %d' % n
        print 'PUSHFQ'
        print '.endr'
    if 'POPW' in line and 'FS' in line:
        print '.rept %d' % n
        print 'PUSHW FS'
        print '.endr'
    if 'POP ' in line and 'FS' in line:
        print '.rept %d' % n
        print 'PUSH  FS'
        print '.endr'
    if 'POPW' in line and 'GS' in line:
        print '.rept %d' % n
        print 'PUSHW GS'
        print '.endr'
    if 'POP ' in line and 'GS' in line:
        print '.rept %d' % n
        print 'PUSH  GS'
        print '.endr'
    if readmode:
        print 'XOR R9, R9'
        print 'MFENCE'
        print 'RDTSCP'
        print 'MOV R9d, EAX'
    if 'DIV' in line:
        print 'MOVQ RAX, 0' # to make DIVs work - small results
        print 'MOVQ RDX, 0' # to make DIVs work - small results
    if 'XSAVE' in line:
        print 'MOVQ RAX, 0' # XSAVE checks these bits
        print 'MOVQ RDX, 0' # 
    print '.rept %d' % n
    print line
    print '.endr'
    print '3:'
    if readmode:
#        print 'MFENCE'
        print 'RDTSCP'
        print 'SUB EAX, R9d'
#        print 'ANDQ RAX, 4294967295'
    print 'MOV R8, OFFSET keepsp'
    print 'MOV RSP, [R8]'
    print 'POP R15'
    print 'POP R14'
    print 'POP R13'
    print 'POP R12'
    print 'POP RBX'
    print 'POP RBP'
    print '4: RET'
    print '.section .data'
    assert '"' not in line
    print '%s: .ascii "%s" ; .byte 0' % (asmlabelname, line)
    print '.section .text'
    if 'CALL ' in line:
        assert '[RSI]' in line or ' R8' in line or 'genericret' in line
    return labelname, asmlabelname

if __name__ == "__main__":
    main()
