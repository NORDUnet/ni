from django import forms
from datetime import date, timedelta

OPERATIONAL_STATE = [
    ('In service', 'In service'),
    ('Decommissioned', 'Decommissioned'),
    ('Testing', 'Testing'),
    ('Reserved', 'Reserved'),
    ('Not set', 'Not set'),
]


class HostReportForm(forms.Form):
    operational_state = forms.MultipleChoiceField(choices=OPERATIONAL_STATE, required=False,
                                                  widget=forms.CheckboxSelectMultiple)
    cut_off = forms.ChoiceField(
        choices=[('1', 'Present'), ('14', 'Last 14 days'), ('30', 'Last 30 days'), ('All', 'All')],
        required=False, initial='All')

    def to_where(self, host="host", additional=None):
        q = ""
        conditions = _append_not_empty([], additional)
        if self.is_valid():
            data = self.cleaned_data
            if data['cut_off'] and data['cut_off'] != "All":
                cut_off = (date.today() - timedelta(int(data['cut_off']))).strftime("%Y-%m-%d")
                conditions.append("toString({host}.noclook_last_seen) >= '{cut_off}'".format(host=host, cut_off=cut_off))
            if data['operational_state']:
                no_state = None
                if "Not set" in data['operational_state']:
                    data['operational_state'].remove("Not set")
                    no_state = "NOT HAS({host}.operational_state)".format(host=host)
                q_state = "{host}.operational_state=".format(host=host)+"'{state}'"
                states = _append_not_empty([q_state.format(state=state) for state in data['operational_state']], no_state)
                conditions.append(" or ".join(states))
        if conditions:
            q = " WHERE (" + ") and (".join(conditions)+")"
        return q


def _append_not_empty(arr, item):
    if item:
        arr.append(item)
    return arr
