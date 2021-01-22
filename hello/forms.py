from django import forms


class ReportForm(forms.Form):
    twitter_accounts = forms.CharField(label=False, max_length=3000, widget=forms.Textarea(
        attrs={'placeholder': "YourFirstSpammer\nYourSecondSpammer\n1314382884006842368"}))
    block_option = forms.BooleanField(label="Block reported accounts", required=False)
