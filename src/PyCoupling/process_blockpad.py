#---------------------------------------------------------------------------
# File:         process_blockpad.py
# Description:  Autonumbers blockpad generated PDFs and generated a table of contents.
# Copyright 2023 by Russell Carroll
#---------------------------------------------------------------------------

import fitz
import sys
import pprint
from math import ceil, floor
from PIL import Image, ImageDraw, ImageFont

pp = pprint.PrettyPrinter(indent=4)
# Install "fitz" package with: python -m pip install --upgrade pymupdf

fn = sys.argv[1]

doc = fitz.open(fn)

print("Page Count: {}".format(doc.page_count))
print("Table of contents: \n{}".format(doc.get_toc()))
print("Metadata: \n{}".format(doc.metadata))

r_page_cnt = fitz.Rect(525, 34, 590, 48)
r_section_nm = fitz.Rect(253, 66, 515, 85)

r_section_toc_header = fitz.Rect(28.8, 95, 580, 118)
r_section_toc_cont = fitz.Rect(28.8, 132, 580, 717)
r_section_toc_page = fitz.Rect(530, 132, 590, 717)

#Rect(253.5, 66.97573852539062, 513.93994140625, 79.52574157714844)

black = (0,0,0)
white = (1,1,1)

TOC_PG_LINES = 45
SECT_SZ = 100
WIDTH_GOAL = 525

font_reg = "F5"
font_bold = "F6"

#pp.pprint(doc.get_page_fonts(3, full=False))

# Scan for contents
#contents = [[SECT_SZ, "Cover Page", 1]]
contents = []
cur_sect = ""
for page in doc:
    # Ignore cover page
    #print(page.search_for("Table of Contents"))
    if page.number > 0:
        # Get Section
        sect = page.get_textbox(r_section_nm).strip()
        if not(sect == cur_sect):
            contents.append([SECT_SZ, sect, page.number])
            cur_sect = sect
        blocks = page.get_text("dict", flags=11)["blocks"]
        for b in blocks:  # iterate through the text blocks
            for l in b["lines"]:  # iterate through the text lines
                for s in l["spans"]:  # iterate through the text spans
                    try:
                        sz = int(s["size"])
                        if (sz > 12) and (s["font"] == "Muli-Regular"):
                            contents.append([sz, s["text"], page.number])
                    except:
                        pass

print("Contents:")
pp.pprint(contents)

# Calculate number pages needed for TOC
sect_cnt = 0
toc_pn_first = 0
for cont in contents:
    if cont[0] == SECT_SZ:
        sect_cnt += 1
    if (cont[1] == "Table of Contents") and (toc_pn_first == 0):
        toc_pn_first = cont[2]

TOC_PAGES = int(ceil((len(contents)+sect_cnt)/TOC_PG_LINES))
print("TOC Page Count: {}".format(TOC_PAGES))

# Get tab offsets
heir = sorted(set([cont[0] for cont in contents])) # Get unique list of sorted sizes
tab_dict = {}
for ind in range(len(heir)):
    tab_dict[heir.pop()] = ind

line_leader = " " + "".join(["."]*200)

# Copy extra TOC pages

"""
print("Fonts:")
print(doc[1].get_fonts())
print()
#"""

widthlist = doc.get_char_widths(xref=5)
test_fontsize = 10
lead_width = widthlist[ord("'")][1] * test_fontsize

cont_cnt = 0
if toc_pn_first == 0:
    print("Error: Table of Contents template is missing. Skipping TOC generation")
else:
    for ind in range(TOC_PAGES - 1):
        doc.fullcopy_page(toc_pn_first, toc_pn_first)

    # Populate TOC
    for toc_pg in range(TOC_PAGES):
        page = doc[toc_pg + toc_pn_first]
        
        page.clean_contents()
        shape = page.new_shape()
        shape.draw_rect(r_section_toc_header)
        shape.draw_rect(r_section_toc_cont)
        shape.finish(width = 0.1, color=white, fill=white)
        
        if toc_pg == 0:
            hdr_txt = "Table of Contents"
        else:
            hdr_txt = "Table of Contents cont."
        
        toc_cont = ""
        toc_line = 0
        page_txt = ""
        while (toc_line < TOC_PG_LINES) and (cont_cnt < len(contents)):
            cont = contents[cont_cnt]
            cont_cnt += 1
            
            tab = "".join(["   "]*tab_dict[cont[0]])
            cont_txt = tab + cont[1] + " "
            
            
            
            width_raw = sum([widthlist[ord(c)][1] for c in cont_txt]) * test_fontsize
            
            N_lead = int(floor((WIDTH_GOAL-width_raw)/lead_width))
            for ind in range(N_lead):
                cont_txt += "."
            
            """
            width = 0
            for c in cont_txt:
                width += test_font.getsize(c)[0]
            
            while width < WIDTH_GOAL:
                cont_txt += '.'
                width += test_font.getsize('.')[0]
            """
            
            page_num = cont[2]
            if page_num > toc_pn_first:
                page_num += TOC_PAGES - 1
            
            if cont[0] == SECT_SZ:
                toc_cont += "\n{}\n".format(cont_txt)
                page_txt += "\n {}\n".format(page_num)
                toc_line += 2
            else:
                
                toc_cont += "{}\n".format(cont_txt)
                page_txt += " {}\n".format(page_num)
                toc_line += 1
            
        toc_cont = toc_cont.strip()
        page_txt = " " + page_txt.strip()
        
        shape.insert_textbox(r_section_toc_header, hdr_txt, color=black, align=fitz.TEXT_ALIGN_LEFT, fontname = font_reg, fontsize=16) #, rotate=0)
        shape.insert_textbox(r_section_toc_cont, toc_cont, color=black, align=fitz.TEXT_ALIGN_LEFT, fontname = font_reg, fontsize=10) #, rotate=0)
        shape.commit()
        
        shape = page.new_shape()
        shape.draw_rect(r_section_toc_page)
        shape.finish(width = 0.1, color=white, fill=white)
        shape.insert_textbox(r_section_toc_page, page_txt, color=black, align=fitz.TEXT_ALIGN_LEFT, fontname = font_reg, fontsize=10) #, rotate=0)
        shape.commit()
        
# Renumber pages
for page in doc:
    if page.number > 0:
        page.clean_contents()
        shape = page.new_shape()
        shape.draw_rect(r_page_cnt)
        shape.finish(width = 0.1, color=white, fill=white)
        
        text = "{} / {}".format(page.number, doc.page_count - 1)
        rc = shape.insert_textbox(r_page_cnt, text, color=black, align=fitz.TEXT_ALIGN_CENTER, fontname = "F5", fontsize=11) #, rotate=0)
        shape.commit()

doc.save(fn.replace(".pdf","_mod.pdf"))
