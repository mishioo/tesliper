###################
###   IMPORTS   ###
###################

import csv
import numpy as np
import logging as lgg
import os
import openpyxl as oxl


##################
###   LOGGER   ###
##################

logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)

    
###################
###   CLASSES   ###
###################

class Writer:

    def __init__(self, tesliper):
        self.ts = tesliper
        
    def save_output(self, *args, output_dir):
        #populations, bars (with e-m), spectra, averaged, settings
        if 'popul' in args:
            self._export_ens_txt_collectively(output_dir)
            # for en in self.energies.values():
                # path = os.path.join(output_dir,
                                    # 'Distribution.{}.txt'.format(en.type))
                # f = open(path, 'w', newline='')
                # writer = csv.writer(f, delimiter='\t')
                # writer.writerow(['Gaussian output file', 'Population', 'DE',
                                 # 'Energy', 'Imag', 'Stoichiometry'])
                # writer.writerows([[f, p, d, e, i, s] for f, p, d, e, i, s in \
                    # zip(en.filenames, en.populations, en.deltas, en.values,
                        # self.bars.iri.imag.sum(0), en.stoich)])
                # f.close()
        if 'ens' in args:
            self._export_ens_txt_separately(output_dir)
        if 'bars' in args:
            self._export_bars_txts(path=output_dir)
        if 'spectra' in args:
            for spc in self.spectra.values():
                spc.export_txts(path=output_dir)
            self.ts.logger.info("Individual conformers' spectra text export done.")
                    
        if 'averaged' in args:
            pass
        if 'settings' in args:
            pass
    
    __header = dict(
        rot = 'Rot. Str. ',
        dip = 'Dip. Str. ',
        roa1 = 'ROA1      ',
        raman1 = 'Raman1    ',
        vrot = 'Rot.(velo)',
        lrot = 'Rot. (len)',
        vosc = 'Osc.(velo)',
        losc = 'Osc. (len)',
        iri = 'IR Int.   ',
        vemang = 'E-M Angle ',
        eemang = 'E-M Angle ',
        zpe = 'Zero-point',
        ten = 'Thermal',
        ent = 'Enthalpy',
        gib = 'Gibbs',
        scf = 'SCF',
        ex_en = 'Excit. Energy',
        freq = 'Frequency ',
        wave = 'Wavelenght'
        )
    
    __formatters = dict(
        rot = '{:> 10.4f}',
        dip = '{:> 10.4f}',
        roa1 = '{:> 10.4f}',
        raman1 = '{:> 10.4f}',
        vrot = '{:> 10.4f}',
        lrot = '{:> 10.4f}',
        vosc = '{:> 10.4f}',
        losc = '{:> 10.4f}',
        iri = '{:> 10.4f}',
        vemang = '{:> 10.4f}',
        eemang = '{:> 10.4f}',
        zpe = '{:> 13.4f}',
        ten = '{:> 13.4f}',
        ent = '{:> 13.4f}',
        gib = '{:> 13.4f}',
        scf = '{:> 13.4f}',
        ex_en = '{:> 13.4f}',
        freq = '{:> 10.2f}',
        wave = '{:> 10.2f}'
        )
        
    energies_order = 'zpe ten ent gib scf'.split(' ')
    
    def _export_ens_txt_separately(self, path):
        h = ' | '.join(['Population / %', 'Min. B. Factor',
                       'DE / (kcal/mol)', 'Energy / Hartree', 'Imag'])
        for key, en in self.ts.energies.items():
            max_fnm = max(np.vectorize(len)(en.filenames).max(), 20)
            max_stoich = max(np.vectorize(len)(en.stoich).max(), 13)
            file_path = os.path.join(path, '!distribution.{}.txt'.format(key))
            header = '{:<{w}} | '.format('Gaussian output file', w=max_fnm) + h
            header = header + ' | {:<{w}}'.format('Stoichiometry', w=max_stoich)
            with open(file_path, 'w') as file:
                file.write(header + '\n')
                file.write('-' * len(header) + '\n')
                for row in zip(en.filenames, en.populations * 100,
                               en.min_factor, en.deltas, en.values,
                               self.bars.iri.imag.sum(0), en.stoich):
                    row = ['{:^{w}{f}}'.format(v, w=w, f=f) \
                        for v, w, f in zip(row, 
                            (max_fnm, 14, 14, 15, 16, 4, max_stoich),
                            ('', '.4f', '.4f', '.4f', 'f', 'd', ''))]
                    file.write(' | '.join(row) + '\n')
        
    def _export_ens_txt_collectively(self, path):
        self.ts.unify_data(data_type='e')
            #or rather check if unified?
            #or maybe contextmanager with unified: ... ?
        ens = [self.ts.energies[en] for en in self.energies_order]
            #get them sorted
        filenames = ens[0].filenames
        longest = max(np.vectorize(len)(filenames).max(), 20)
        types = [en.type for en in ens]
        values = np.array([en.values for en in ens]).T
        #deltas = np.array([en.deltas for en in ens])
        popul = np.array([en.populations * 100 for en in ens]).T
        header = '{:<{lgst}} | {:^50} | {:^70}'.format('Gaussian output file',
            'Population / %', 'Energy / Hartree', lgst=longest)
        names = [self.__header[en] for en in self.energies_order]
        with open(os.path.join(path, '!distribution.txt'), 'w') as file:
            file.write(header + '\n')
            names_line = ' ' * longest + ' | ' + \
                '  '.join(['{:<{w}}'.format(n, w=max(8, len(n))) \
                           for n in names]) + ' | ' + \
                '  '.join(['{:<{w}}'.format(n, w=14 if n=='SCF' else 12) \
                           for n in names]) + '\n'
            file.write(names_line)
            file.write('-' * len(header) + '\n')
            for fnm, vals, pops in zip(filenames, values, popul):
                p_line = '  '.join(
                    ['{:>{w}.4f}'.format(p, w=max(8, len(n))) \
                     for p, n in zip(pops, names)])
                v_line = '  '.join(
                    ['{:> {w}.{prec}f}'.format(v, w=14 if n=='SCF' else 12,
                                               prec=8 if n=='SCF' else 6) \
                     for v, n in zip(vals, names)])
                line = fnm + ' | ' + p_line + ' | ' + v_line + '\n'
                file.write(line)

    def __format_header(self, bar_names):
        pass
        
    def __format_line(self, bar_names, values):
        pass
            
    def _export_bars_txts(self, path):
        separated = defaultdict(list)
        for bar in self.ts.bars.values():
            separated[bar._soxhlet_id].append(bar)
        order = 'dip rot raman1 roa1 vemang vrot vosc lrot losc eemang'\
                .split(' ')
        sox_ref = {'=vcd': 'vibra',
                   '=roa': 'raman',
                   'td=': 'electr'}
        for sox_id, bars in separated.items():
            com = self.ts.soxhlet.instances[sox_id].command
            _type = [val for key, val in sox_ref.items() if key in com][0]
            bars_sorted = \
                [bar for name in order for bar in bars if bar.type == name]
            freq_type = 'wave' if _type == 'electr' else 'freq'
            values_sorted = [iter(bar.values) for bar in bars_sorted]
            frequencies = iter(bars[0].full.frequencies)
            self.ts.logger.debug('Will make an attempt to export data to txt '
                                 'from soxhlet {}.'.format(sox_id))
            if not bars_sorted:
                self.ts.logger.debug('This soxhlet instance have not provided '
                                     'any exportable data. Continuing to next '
                                     'soxhlet.')
                continue
            self.tslogger.debug('This soxhlet instance provided following data'
                         ' types: {}.'.format(', '.join([bar.type for bar \
                                                         in bars_sorted])))
            for fname in self.ts.soxhlet.instances[sox_id].gaussian_files:
                values, types = zip(
                    *[(next(val), bar.type) for val, bar
                      in zip(values_sorted, bars_sorted)
                      if fname in bar.filenames])
                freqs = [next(frequencies)]
                if values:
                    values = freqs + list(values)
                    types = [freq_type] + list(types)
                    filename = '{}.{}.bar'.format('.'.join(fname.split('.')[:-1]), _type)
                    self.__export_file_txt(path, filename, types, np.array(values).T)
        self.ts.logger.info('Bars export to text files done.')
                    
    def __export_file_txt(self, path, filename, types, values_list):
        with open(os.path.join(path, filename), 'w') as file:
            file.write('\t'.join([self.__header[type] for type in types]))
            file.write('\n')
            for values in values_list:
                line = '\t'.join(self.__formatters[tp].format(v) for v, tp in zip(values, types))
                file.write(line + '\n')

    def export_energies_xlsx(self):
        wb = oxl.Workbook()
        ws = wb.active
        ws.title = 'Collective overview'
        ws['A1'] = 'Output Gaussian file'
        ws['B1'] = 'Populations / %'
        ws['G1'] = 'Energies / hartree'
        names = [self.__header[en] for en in self.energies_order]
        ws.append([''] + names + names)
        ws.merge_cells('A1:A2')
        ws.merge_cells('B1:F1')
        ws.merge_cells('G1:K1')
        with self.ts.unified_data(data_type='e') as data:
            filenames = data['scf'].filenames
            values = [data[en].values for en in self.energies_order]
            populs = [data[en].populations for en in self.energies_order]
            for row in zip(filenames, *populs, *values):
                ws.append(row)
        wb.save(os.path.join(self.ts.output_dir, '!distribution.xlsx'))