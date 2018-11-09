###################
###   IMPORTS   ###
###################

import csv
import numpy as np
import logging as lgg
import os
import openpyxl as oxl
from collections import defaultdict

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
        self.path = os.getcwd()

    @property
    def path(self):
        return self.__path

    @path.setter
    def path(self, value):
        if not os.path.isdir(value):
            raise FileNotFoundError(
                f'Path {value} does not exists or is not a directory.'
            )
        else:
            self.__path = value


    @property
    def distribution_center(self):
        return dict(
            energies={'txt': self.energies_txt,
                      'csv': self.energies_csv,
                      'xlsx': self.energies_xlsx},
            bars={'txt': self.bars_txt,
                  'csv': self.bars_csv,
                  'xlsx': self.bars_xlsx},
            spectra={'txt': self.spectra_txt,
                     'csv': self.spectra_csv,
                     'xlsx': self.spectra_xlsx},
            averaged={'txt': self.averaged_txt,
                      'csv': self.averaged_csv,
                      'xlsx': self.averaged_xlsx}
        )

    def save_output(self, output, format=None, output_dir=None):
        output_dir = output_dir if output_dir else self.ts.output_dir
        self.path = output_dir
        format = ['txt'] if not format else [format] \
            if not isinstance(format, (list, tuple)) else format
        output = output if isinstance(output, (list, tuple)) else [output]
        functions = []
        for thing in output:
            for fmt in format:
                try:
                    functions.append(self.distribution_center[thing][fmt])
                except KeyError:
                    logger.error('Can not export {} as {}. No such '
                                 'thing or unsupported format.'.format(thing,
                                                                       fmt))
        for func in functions:
            func()

    __header = dict(
        freq='Frequencies',
        mass=r'Red. masses',
        frc=r'Frc consts',
        raman=r'Raman Activ',
        depolarp=r'Depolar \(P\)',
        depolaru=r'Depolar \(U\)',
        ramact=r'RamAct',
        depp=r'Dep-P',
        depu=r'Dep-U',
        alpha2=r'Alpha2',
        beta2=r'Beta2',
        alphag=r'AlphaG',
        gamma2=r'Gamma2',
        delta2=r'Delta2',
        cid1=r'CID1',
        raman2=r'Raman2',
        roa2=r'ROA2',
        cid2=r'CID2',
        raman3=r'Raman3',
        roa3=r'ROA3',
        cid3=r'CID3',
        rc180=r'RC180',
        rot='Rot. Str.',
        dip='Dip. Str.',
        roa1='ROA1',
        raman1='Raman1',
        ex_en='Excit. Energy',
        wave='Wavelenght',
        vrot='Rot.(velo)',
        lrot='Rot. (len)',
        vosc='Osc.(velo)',
        losc='Osc. (len)',
        iri='IR Int.',
        emang='E-M Angle',
        eemang='E-M Angle',
        zpe='Zero-point',
        ten='Thermal',
        ent='Enthalpy',
        gib='Gibbs',
        scf='SCF'
    )

    __formatters = dict(
        rot='{:> 10.4f}',
        dip='{:> 10.4f}',
        roa1='{:> 10.4f}',
        raman1='{:> 10.4f}',
        vrot='{:> 10.4f}',
        lrot='{:> 10.4f}',
        vosc='{:> 10.4f}',
        losc='{:> 10.4f}',
        iri='{:> 10.4f}',
        emang='{:> 10.4f}',
        eemang='{:> 10.4f}',
        zpe='{:> 13.4f}',
        ten='{:> 13.4f}',
        ent='{:> 13.4f}',
        gib='{:> 13.4f}',
        scf='{:> 13.4f}',
        ex_en='{:> 13.4f}',
        freq='{:> 10.2f}',
        wave='{:> 10.2f}',
        mass=r'{:> 11.4f}',
        frc=r'{:> 10.4f}',
        raman=r'{:> 11.4f}',
        depolarp=r'{:> 11.4f}',
        depolaru=r'{:> 11.4f}',
        ramact=r'{:> 10.4f}',
        depp=r'{:> 9.4f}',
        depu=r'{:> 9.4f}',
        alpha2=r'{:> 9.4f}',
        beta2=r'{:> 9.4f}',
        alphag=r'{:> 9.4f}',
        gamma2=r'{:> 9.4f}',
        delta2=r'{:> 9.4f}',
        cid1=r'{:> 8.3f}',
        raman2=r'{:> 8.3f}',
        roa2=r'{:> 8.3f}',
        cid2=r'{:> 8.3f}',
        raman3=r'{:> 8.3f}',
        roa3=r'{:> 8.3f}',
        cid3=r'{:> 8.3f}',
        rc180=r'{:> 8.3f}',
    )

    __excel_formats = dict(
        freq='0.0000',
        mass=r'0.0000',
        frc=r'0.0000',
        raman=r'0.0000',
        depolarp=r'0.0000',
        depolaru=r'0.0000',
        ramact=r'0.0000',
        depp=r'0.0000',
        depu=r'0.0000',
        alpha2=r'0.0000',
        beta2=r'0.0000',
        alphag=r'0.0000',
        gamma2=r'0.0000',
        delta2=r'0.0000',
        cid1=r'0.000',
        raman2=r'0.000',
        roa2=r'0.000',
        cid2=r'0.000',
        raman3=r'0.000',
        roa3=r'0.000',
        cid3=r'0.000',
        rc180=r'0.000',
        rot='0.0000',
        dip='0.0000',
        roa1='0.000',
        raman1='0.000',
        ex_en='0.0000',
        wave='0.0000',
        vrot='0.0000',
        lrot='0.0000',
        vosc='0.0000',
        losc='0.0000',
        iri='0.0000',
        emang='0.0000',
        eemang='0.0000',
        zpe='0.000000',
        ten='0.000000',
        ent='0.000000',
        gib='0.000000',
        scf='0.00000000'
    )

    energies_order = 'zpe ten ent gib scf'.split(' ')

    def energies_txt(self):
        self._energies_txt_collectively()
        self._energies_txt_separately()

    def _energies_txt_separately(self):
        h = ' | '.join(['Population/%', 'Min.B.Factor',
                        'DE/(kcal/mol)', 'Energy/Hartree'])
        align = ('<', '>', '>', '>', '>', '>')
        for key, en in self.ts.energies.items():
            max_fnm = max(np.vectorize(len)(en.filenames).max(), 20)
            file_path = os.path.join(self.path, f'distribution.{key}.txt')
            header = '{:<{w}} | '.format('Gaussian output file', w=max_fnm) + h
            width = (max_fnm, 12, 12, 13, 14, 12)
            if key != 'scf':
                header = header + ' | Corr/Hartree'
                corrections = self.ts.molecules.arrayed(f'{key}corr')
                rows = zip(en.filenames, en.populations * 100, en.min_factors,
                           en.deltas, en.values, corrections.values)
                fmt = ('', '.4f', '.4f', '.4f', '.6f', 'f')
            else:
                rows = zip(en.filenames, en.populations * 100, en.min_factors,
                           en.deltas, en.values)
                fmt = ('', '.4f', '.4f', '.4f', '.8f', 'f')
            with open(file_path, 'w') as file:
                file.write(header + '\n')
                file.write('-' * len(header) + '\n')
                for row in rows:
                    new_row = [
                        '{:{a}{w}{f}}'.format(v, a=a, w=w, f=f)
                        for v, a, w, f in zip(row, align, width, fmt)
                    ]
                    file.write(' | '.join(new_row) + '\n')
        logger.info('Energies separate export to text files done.')

    def _energies_txt_collectively(self):
        data = self.ts.energies
        ens = [data[en] for en in self.energies_order]
        # get them sorted
        filenames = ens[0].filenames
        with self.ts.molecules.trimmed_to(filenames) as mols:
            imaginary = mols.arrayed('iri').imaginary
            stoichiometry = mols.arrayed('stoichiometry').values
        max_fnm = max(np.vectorize(len)(filenames).max(), 20)
        max_stoich = max(np.vectorize(len)(stoichiometry).max(), 13)
        values = np.array([en.values for en in ens]).T
        # deltas = np.array([en.deltas for en in ens])
        popul = np.array([en.populations * 100 for en in ens]).T
        header = '{:<{lgst}} | {:^50} | {:^70} | Imag | {:<{stoich}}'.format(
            'Gaussian output file', 'Population / %', 'Energy / Hartree',
            'Stoichiometry', lgst=max_fnm, stoich=max_stoich)
        names = [self.__header[en] for en in self.energies_order]
        fname = 'distribution_overview.txt'
        with open(os.path.join(self.path, fname), 'w') as file:
            file.write(header + '\n')
            names_line = \
                ' ' * max_fnm + ' | ' + \
                '  '.join(
                    ['{:<{w}}'.format(n, w=max(8, len(n))) for n in names]
                ) + ' | ' + \
                '  '.join(
                    ['{:<{w}}'.format(n, w=14 if n == 'SCF' else 12)
                     for n in names]
                ) + ' |      |\n'
            file.write(names_line)
            file.write('-' * len(header) + '\n')
            rows = zip(filenames, values, popul, imaginary, stoichiometry)
            for fnm, vals, pops, imag, stoich in rows:
                p_line = '  '.join(
                    ['{:>{w}.4f}'.format(p, w=max(8, len(n)))
                     for p, n in zip(pops, names)]
                )
                v_line = '  '.join(
                    ['{:> {w}.{prec}f}'.format(v, w=14 if n == 'SCF' else 12,
                                               prec=8 if n == 'SCF' else 6)
                     for v, n in zip(vals, names)]
                )
                line = '{:<{w}}'.format(fnm, w=max_fnm) + ' | ' + p_line + \
                       ' | ' + v_line + f' | {imag:^ 4}' + \
                       ' | {:<{w}}'.format(stoich, w=max_stoich) + '\n'
                file.write(line)
        logger.info('Energies collective export to text file done.')

    def energies_xlsx(self):
        wb = oxl.Workbook()
        ws = wb.active
        ws.title = 'Collective overview'
        ws['A1'] = 'Gaussian output file'
        ws['B1'] = 'Populations / %'
        ws['G1'] = 'Energies / hartree'
        ws['L1'] = 'Imag'
        ws['M1'] = 'Stoichiometry'
        names = [self.__header[name] for name in self.energies_order]
        ws.append([''] + names + names)
        ws.merge_cells('A1:A2')
        ws.merge_cells('B1:F1')
        ws.merge_cells('G1:K1')
        ws.merge_cells('L1:L2')
        ws.merge_cells('M1:M2')
        ws.freeze_panes = 'A3'
        data = self.ts.energies
        filenames = data['gib'].filenames
        fmts = ['0'] + ['0.00%'] * 5 + ['0.000000'] * 4 + \
               ['0.00000000', '0', '0']
        with self.ts.molecules.trimmed_to(filenames) as mols:
            values = [data[name].values for name in self.energies_order]
            populs = [data[name].populations for name in self.energies_order]
            imag = mols.arrayed('iri').imaginary
            stoich = mols.arrayed('stoichiometry').values
            rows = zip(filenames, *populs, *values, imag, stoich)
            for row_num, values in enumerate(rows):
                for col_num, (fmt, value) in enumerate(zip(fmts, values)):
                    cell = ws.cell(row=row_num+3, column=col_num+1)
                    cell.value = value
                    cell.number_format = fmt
        # set cells width
        widths = [0] + [10] * 5 + [14] * 4 + [16, 6, 0]
        for column, width in zip(ws.columns, widths):
            if not width:
                width = max(len(str(cell.value)) for cell in column) + 2
            ws.column_dimensions[column[0].column].width = width
        # proceed to write detailed info on separate sheet for each energy
        for key in self.energies_order:
            fmts = ['0', '0.00%'] + ['0.0000'] * 2 + \
                   ['0.00000000' if key == 'scf' else '0.000000'] * 2
            ws = wb.create_sheet(title=self.__header[key])
            en = data[key]
            ws.freeze_panes = 'A2'
            if key != 'scf':
                corr = self.ts.molecules.arrayed(f'{key}corr')
                header = ['Gaussian output file', 'Population / %',
                          'Min. B. Factor', 'DE / (kcal/mol)',
                          'Energy / Hartree', 'Correction / Hartree']
                rows = zip(en.filenames, en.populations, en.min_factors,
                           en.deltas, en.values, corr.values)
            else:
                header = ['Gaussian output file', 'Population / %',
                          'Min. B. Factor', 'DE / (kcal/mol)',
                          'Energy / Hartree']
                rows = zip(en.filenames, en.populations, en.min_factors,
                           en.deltas, en.values)
            ws.append(header)
            for row_num, values in enumerate(rows):
                for col_num, (fmt, value) in enumerate(zip(fmts, values)):
                    cell = ws.cell(row=row_num+2, column=col_num+1)
                    cell.value = value
                    cell.number_format = fmt
            # set cells width
            widths = [0, 15, 14, 15, 16, 19]
            for column, width in zip(ws.columns, widths):
                if not width:
                    width = max(len(str(cell.value)) for cell in column) + 2
                ws.column_dimensions[column[0].column].width = width
        wb.save(os.path.join(self.path, 'distribution.xlsx'))
        logger.info('Energies export to xlsx files done.')

    def energies_csv(self):
        header = 'population min_factor delta energy'.split(' ')
        header = ['Gaussian output file'] + header
        for key, en in self.ts.energies.items():
            file_path = os.path.join(self.path,
                                     'distribution.{}.csv'.format(key))
            if key == 'scf':
                rows = zip(en.filenames, en.populations, en.min_factors,
                           en.deltas, en.values)
            else:
                corr = self.ts.molecules.arrayed(f'{key}corr')
                rows = zip(en.filenames, en.populations, en.min_factors,
                           en.deltas, en.values, corr.values)
            with open(file_path, 'w', newline='') as file:
                csvwriter = csv.writer(file)
                csvwriter.writerow(
                    header if key == 'scf' else header + ['corrections']
                )
                for row in rows:
                    csvwriter.writerow(row)
        logger.info('Energies export to csv files done.')

    def _get_ground_bars(self, wanted=None):
        if not wanted:
            wanted = 'freq iri dip rot ramact raman1 roa1 emang'.split(' ')
        else:
            ground_bars = set(self.ts.molecules.vibrational_keys)
            wanted = [bar for bar in wanted if bar in ground_bars]
        for fname, mol in self.ts.molecules.trimmed_items():
            bars = [bar for bar in wanted if bar in mol]
            yield fname, bars, [mol[v] for v in bars]

    def _get_excited_bars(self, wanted=None):
        if not wanted:
            wanted = 'wave ex_en vrot vosc vdip lrot losc ldip ' \
                     'eemang'.split(' ')
        else:
            excited_bars = set(self.ts.molecules.electronic_keys)
            wanted = [bar for bar in wanted if bar in excited_bars]
        for fname, mol in self.ts.molecules.trimmed_items():
            bars = [bar for bar in wanted if bar in mol]
            yield fname, bars, [mol[v] for v in bars]

    def bars_txt(self, wanted=None):
        for key, getter in (('v', self._get_ground_bars(wanted)),
                            ('e', self._get_excited_bars(wanted))):
            for fname, bars, values in getter:
                filename = f"{'.'.join(fname.split('.')[:-1])}.{key}.txt"
                if not bars:
                    continue
                with open(os.path.join(self.path, filename), 'w') as file:
                    headers = [self.__header[bar] for bar in bars]
                    widths = [self.__formatters[bar][4:6] for bar in bars]
                    formatted = [f'{h: <{w}}' for h, w in zip(headers, widths)]
                    file.write('\t'.join(formatted))
                    file.write('\n')
                    for vals in zip(*values):
                        line = '\t'.join(self.__formatters[b].format(v)
                                         for v, b in zip(vals, bars))
                        file.write(line + '\n')
        logger.info('Bars export to text files done.')

    def bars_csv(self, wanted=None):
        for key, getter in (('v', self._get_ground_bars(wanted)),
                            ('e', self._get_excited_bars(wanted))):
            for fname, bars, values in getter:
                if not bars:
                    continue
                filename = f"{'.'.join(fname.split('.')[:-1])}.{key}.csv"
                path = os.path.join(self.path, filename)
                with open(path, 'w', newline='') as file:
                    csvwriter = csv.writer(file)
                    headers = [self.__header[bar] for bar in bars]
                    csvwriter.writerow(headers)
                    for row in zip(*values):
                        csvwriter.writerow(row)
        logger.info('Bars export to csv files done.')

    def bars_xlsx(self, wanted=None):
        wbs = {key: oxl.Workbook() for key in ('ground_state', 'excited_state')}
        getters = {'ground_state': self._get_ground_bars(wanted),
                   'excited_state': self._get_excited_bars(wanted)}
        for key, wb in wbs.items():
            wb.remove(wb.active)
            got_something = False
            for fname, bars, values in getters[key]:
                if not bars:
                    continue
                got_something = True
                ws = wb.create_sheet(fname)
                headers = [self.__header[bar] for bar in bars]
                widths = [max(len(h), 10) for h in headers]
                fmts = [self.__excel_formats[bar] for bar in bars]
                ws.append(headers)
                ws.freeze_panes = 'B2'
                for column, width in zip(ws.columns, widths):
                    ws.column_dimensions[column[0].column].width = width
                for col_num, (vals, fmt) in enumerate(zip(values, fmts)):
                    for row_num, v in enumerate(vals):
                        cell = ws.cell(row=row_num+2, column=col_num+1)
                        cell.value = v
                        cell.number_format = fmt
            if got_something:
                wb.save(os.path.join(self.path, 'bars_' + key + '.xlsx'))
        logger.info('Bars export to xlsx files done.')

    @property
    def exported_filenames(self):
        make_new_names = lambda fnm: \
            '{}.{}.txt'.format('.'.join(fnm.split('.')[:-1]), self.name)
        names = map(make_new_names, self.filenames)
        return names

    @property
    def averaged_filename(self):
        return 'avg_{}_{}'.format(self.name, self.energy_type)

    def spectra_export(self, format=''):
        for spectra in self.ts.spectra.values():
            if format == 'xlsx':
                yield spectra
            else:
                x = spectra.x
                name = spectra.genre
                title = f'{name} calculated with peak width = {spectra.width}' \
                        f' {spectra.units["width"]} and {spectra.fitting} ' \
                        f'fitting, shown as {spectra.units["x"]} vs. ' \
                        f'{spectra.units["y"]}'
                for fnm, y in zip(spectra.filenames, spectra.y):
                    filename = '.'.join(fnm.split('.')[:-1])
                    yield (filename, name, y, x, title)

    def spectra_txt(self):
        for fnm, name, values, base, title in self.spectra_export():
            file_path = os.path.join(self.path, f'{fnm}.{name}.txt')
            with open(file_path, 'w') as file:
                file.write(title + '\n')
                file.write(
                    '\n'.join(
                        '{:>4d}\t{: .4f}'.format(int(b), s)
                        for b, s in zip(base, values)
                    )
                )
        logger.info('Spectra export to text files done.')

    def spectra_csv(self):
        for fnm, name, values, base, title in self.spectra_export():
            file_path = os.path.join(self.path, f'{fnm}.{name}.csv')
            with open(file_path, 'w', newline='') as file:
                csvwriter = csv.writer(file)
                for row in zip(base, values): csvwriter.writerow(row)
        logger.info('Spectra export to csv files done.')

    def spectra_xlsx(self):
        wb = oxl.Workbook()
        del wb['Sheet']
        for spectra in self.spectra_export('xlsx'):
            ws = wb.create_sheet()
            ws.title = spectra.genre
            ws.freeze_panes = 'B2'
            A0 = spectra.units['x']
            ws.append([A0] + list(spectra.filenames))
            title = f'{spectra.genre} calculated with peak width = ' \
                    f'{spectra.width} {spectra.units["width"]} and ' \
                    f'{spectra.fitting} fitting, shown as ' \
                    f'{spectra.units["x"]} vs. {spectra.units["y"]}'
            ws["A1"].comment = oxl.comments.Comment(title, 'Tesliper')
            for line in zip(spectra.x, *spectra.y):
                ws.append(line)
        wb.save(os.path.join(self.path, 'spectra.xlsx'))
        logger.info('Spectra export to xlsx file done.')

    def averaged_export(self):
        for name, spc in self.ts.spectra.items():
            spectra = []
            for en in self.energies_order:
                spectra.append(self.ts.get_averaged_spectrum(name, en))
            yield (name, spc, spectra)

    def averaged_txt(self):
        for name, spectra, averaged in self.averaged_export():
            title = f'{name} calculated with peak width = {spectra.width} ' \
                    f'{spectra.units["width"]} and {spectra.fitting} ' \
                    f'fitting, shown as {spectra.units["x"]} vs. ' \
                    f'{spectra.units["y"]}'
            for en, av in zip(self.energies_order, averaged):
                file_path = os.path.join(self.path,
                                         'averaged.{}.{}.txt'.format(name, en))
                with open(file_path, 'w') as file:
                    file.write(title + '\n')
                    file.write(
                        f'{len(spectra.filenames)} conformers averaged based on'
                        f' {self.__header[en]}\n'
                    )
                    file.write(
                        '\n'.join(
                            f'{int(b):>4d}\t{s: .4f}' for b, s in zip(*av))
                    )
        logger.info('Averaged export to text files done.')

    def averaged_csv(self):
        for name, __, averaged in self.averaged_export():
            for en, av in zip(self.energies_order, averaged):
                file_path = os.path.join(self.path, f'averaged.{name}.{en}.csv')
                with open(file_path, 'w', newline='') as file:
                    csvwriter = csv.writer(file)
                    for row in zip(*av): csvwriter.writerow(row)
        logger.info('Averaged export to csv files done.')

    def averaged_xlsx(self):
        # TO DO: add comment as in txt export
        for name, __, averaged in self.averaged_export():
            wb = oxl.Workbook()
            del wb['Sheet']
            for en, av in zip(self.energies_order, averaged):
                ws = wb.create_sheet()
                ws.title = self.__header[en]
                for row in zip(*av): ws.append(row)
            wb.save(
                os.path.join(self.path, f'averaged.{name}.xlsx')
            )
        logger.info('Averaged export to xlsx files done.')
