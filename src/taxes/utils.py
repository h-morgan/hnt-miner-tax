from typing import no_type_check
import pdfrw

ANNOT_KEY = '/Annots'
ANNOT_FIELD_KEY = '/T'
ANNOT_VAL_KEY = '/V'
ANNOT_RECT_KEY = '/Rect'
SUBTYPE_KEY = '/Subtype'
WIDGET_SUBTYPE_KEY = '/Widget'

PDF_TEXT_APPEARANCE = pdfrw.objects.pdfstring.PdfString.encode('/Courier 8.00 Tf 0 g')


def get_keys_in_pdf(pdf_filestring):
    """
    Gets all they key (field id's) of a fillable pdf
    """
    for page in template_pdf.pages:
        annotations = page[ANNOT_KEY]
        for annotation in annotations:
            if annotation[SUBTYPE_KEY] == WIDGET_SUBTYPE_KEY:
                if annotation[ANNOT_FIELD_KEY]:
                    key = annotation[ANNOT_FIELD_KEY][1:-1]
                    print(key)


def fill_pdf(input_pdf_path, output_pdf_path, data_dict):
    template_pdf = pdfrw.PdfReader(input_pdf_path)
    for page in template_pdf.pages:
        annotations = page[ANNOT_KEY]
        for annotation in annotations:
            if annotation[SUBTYPE_KEY] == WIDGET_SUBTYPE_KEY:
                if annotation[ANNOT_FIELD_KEY]:
                    key = annotation[ANNOT_FIELD_KEY][1:-1]
                    if key in data_dict.keys():
                        if type(data_dict[key]) == bool:
                            if data_dict[key] == True:
                                annotation.update(pdfrw.PdfDict(
                                    AS=pdfrw.PdfName('Yes')))
                        else:
                            #annotation.update({'/DA': PDF_TEXT_APPEARANCE})
                            annotation.update(
                                pdfrw.PdfDict(V='{}'.format(data_dict[key]))
                            )
                            annotation.update(pdfrw.PdfDict(AP=''))
    template_pdf.Root.AcroForm.update(pdfrw.PdfDict(NeedAppearances=pdfrw.PdfObject('true')))  # NEW
    pdfrw.PdfWriter().write(output_pdf_path, template_pdf)


def collect_flags(tax_form):
    """
    Take user-provided form answers and write flags to a dict
    """
    flags = {}
    no_values = ["", "no", "No", "NO"]

    if tax_form['person_moved_states'] not in no_values:
        flags["person_moved_states"] = True

    if tax_form['hotspot_moved_states'] not in no_values:
        flags["hotspot_moved_states"] = True

    if tax_form["llc"]["has_llc"] not in no_values:
        flags["has_llc"] = True
    
    if tax_form["llc"]["single_member"] in ("no", "No"):
        flags["multi_member_llc"] = True

    if tax_form["expenses"]["professional_install"]["type"] == "Independent contractor" and float(tax_form["expenses"]["professional_install"]["cost"]) > 600:
        flags["independent_contractor_over_600"] = True

    if tax_form["expenses"]["other_expenses"]["bool"] not in no_values:
        flags["other_unclaimed_expenses"] = True
    
    if tax_form["expenses"]["hosting"]["had_hosts"] not in no_values:
        if tax_form["expenses"]["hosting"]["payment_currency"] == "HNT":
            flags['paid_hosts_hnt'] = True

    return flags