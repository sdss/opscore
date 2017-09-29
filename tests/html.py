#!/usr/bin/env python
"""Unit tests for opscore.utility.html
"""

# Created 28-Jun-2008 by David Kirkby (dkirkby@uci.edu)
import unittest

from html.parser import HTMLParser
import opscore.utility.html as utilHtml

class HTMLTests(unittest.TestCase):
    @staticmethod
    def validate(doc):
        parser = HTMLParser()
        parser.feed(str(doc))
        parser.close()      
    def test00_HTML(self):
        """Check that skeleton HTML document is correctly formed"""
        doc = utilHtml.HTMLDocument(
            utilHtml.Head(),
            utilHtml.Body()
        )
        self.validate(doc)
    def test01_HTML(self):
        """HTML element access by id"""
        doc = utilHtml.HTMLDocument(
            utilHtml.Head(),
            utilHtml.Body(
                utilHtml.Div('This is the',id='appendme')
            )
        )
        doc['appendme'].append(utilHtml.Span('TITLE',className='bigtext'))
        self.validate(doc)
    def test02_HTML(self):
        """Add external links to css and javascript files"""
        h = utilHtml.Head(title='This is the Title',css='styles1.css')
        h.css += ('styles2.css','styles3.css')
        h.js += ('actions1.js',)
        h.js.append('actions2.js')
    def test03_HTML(self):
        """HTML element attribute accessors"""
        d = utilHtml.Div('This is text within a',utilHtml.Span('red',className='red'),'div element')
        handler = 'clickHandler(this)'
        d['onclick'] = handler
        self.assertEqual(d['onclick'],handler)

if __name__ == '__main__':
    unittest.main()