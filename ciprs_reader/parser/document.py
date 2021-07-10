from ciprs_reader.parser.base import Parser
from ciprs_reader.const import Section
from ciprs_reader.parser.section.offense import OFFENSE_SECTION_PARSERS
from lark import Lark, Transformer
import pprint

class MyTransformer(Transformer):
    def jurisdiction(self, items):
        return " ".join(items)
    def action(self, item):
        (action,) = item
        return "Action", str(action)
    def description(self, items):
        return "Description", " ".join(items)
    def description_ext(self, items):
        return "Description Extended", " ".join(items)
    def severity(self, item):
        (severity,) = item if item else ("",)
        return "Severity", str(severity)
    def law(self, item):
        (law_string,) = item if item else ("",)
        # convert multiple spaces within law into single spaces
        law = ' '.join(law_string.split())
        return "Law", str(law)
    def disposition_method(self, items):
        return " ".join(items)
    def plea(self, items):
        return " ".join(items)
    def verdict(self, items):
        return " ".join(items)
    def disposed_on(self, items):
        return " ".join(items)
    def offense_line(self, items):
        # action description severity law description_ext
        (*fields, last_field) = items
        offense_line_dict = dict(fields)
        (key, value) = last_field
        if key == 'Description Extended':
            offense_line_dict['Description'] = " ".join([offense_line_dict['Description'], value])
        else:
            offense_line_dict[key] = value
        return offense_line_dict

    def offense_section(self, items):
        if not items:
            return None
        return items[0], items[1]
    def offense(self, items):
        offense_dict = {
            'Records': [items[0]],
            'Disposed On': items[4],
            'Disposition Method': items[5],
        }
        if items[1] and items[1]['Description']:
            offense_dict['Records'].append(items[1])
        if items[2]:
            offense_dict['Plea'] = items[2]
        if items[3]:
            offense_dict['Verdict'] = items[3]
        return offense_dict

    document = dict
    offenses = list


class OffenseSectionParser:
    """Only enabled when in offense-related sections."""

    def __init__(self, report, state):
        self.state = state
        self.report = report
        self.parser = Lark(r"""
            document        : (offense_section | _ignore | _IGNORE+)*

            _ignore         : _IGNORE+ _NEWLINE

            offense_section : jurisdiction _ignore? _ignore offenses

            jurisdiction    : JURISDICTION "Court" "Offense" "Information" _NEWLINE

            offenses        : offense+
            offense         : offense_line ~ 2 _offense_info disposition_method _NEWLINE

            _offense_info   : "Plea:" plea "Verdict:" verdict "Disposed" "on:" disposed_on _NEWLINE
            plea            : WORD+ | "-"
            verdict         : WORD+ | "-"
            disposed_on     : TEXT+ | "-"

            disposition_method  : "Disposition" "Method:" TEXT+

            offense_line    : _RECORD_NUM? action description severity law _NEWLINE (description_ext _NEWLINE)*
            _RECORD_NUM     : INT
            action          : ACTION
            description     : TEXT+ | "-"
            severity        : SEVERITY | "-"
            law             : /\S[\S ]+\S/ | "-"
            description_ext : (/(?!(?:Plea:|CONVICTED))\S+/)+

            JURISDICTION    : "District"
                            | "Superior"

            ACTION  : "CHARGED"
                    | "CONVICTED"
                    | "ARRAIGNED"

            SEVERITY    : "TRAFFIC"
                        | "INFRACTION"
                        | "MISDEMEANOR"
                        | "FELONY"

            TEXT        : /\S+/
            _IGNORE     : TEXT | /\f/
            _NEWLINE    : NEWLINE
            _EOL        : /\f/

            %import common.INT
            %import common.WORD
            %import common.WS_INLINE
            %import common.NEWLINE
            %ignore WS_INLINE
        """, start='document')

    def find(self, document):
        tree = self.parser.parse(document)
        data = MyTransformer().transform(tree)
        self.extract(data)

    def extract(self, raw_data):
        if 'District' in raw_data:
            self.report['District Court Offense Information'] = raw_data['District']
        if 'Superior' in raw_data:
            self.report['Superior Court Offense Information'] = raw_data['Superior']
