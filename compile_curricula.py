#!/usr/bin/env python

"""
Compiles the schema and curriculum together

looks in a directory structure like:
pysplash
    lib
        curricula
            course_name
                version
                    schema.xml
                    curriculum.xml
                    spliced.xml
but the rootdir option can move curricula to anywhere
"""

from optparse import OptionParser
from os.path import join
from os import listdir, chdir, getcwd
import re


def add_numbers(curriculum):
    """
    takes a BS4 object; it's a helper for the next function.
    this numbers the units, lessons, assigments in their own orders.
    """

    types = ['content', 'project', 'task', 'self-assessment']

    def number(index, tag, name=''):
        tag['number'] = index
        num = curriculum.new_tag('number')
        num.string = '%s %d' % (name, index) if name else str(index)
        tag.insert(0, num)

    for i, unit in enumerate(curriculum('unit')):
        number(i + 1, unit, 'Unit')
        for j, lesson in enumerate(unit('lesson')):
            number(j + 1, lesson, 'Lesson')
            for k, assignment in enumerate(lesson.find('assignments')(types)):
                number(k + 1, assignment)

    return curriculum


def splice(schema, curriculum):
    for element in schema():
        # [:-1] ignores the [document] tag
        chain = [element.name] + [x.name for x in element.parents][:-1]
        chain.reverse()
        selector = ' > '.join(chain)
        for corresp in curriculum.select(selector):
            for attr in element.attrs:
                corresp[attr] = element[attr]

    return curriculum


def splice_and_save(schm, curr, outf):
    """
    this function takes in a curriculum schema and a curriculum xml file and
    splices them together into something that is inserted into the html page.
    takes in filenames, not bs4 objects. its helper (above) takes bs4 objects.
    to be done once (per curriculum version, that is), then forgotten.
    """

    from bs4.element import Tag
    # the reason we're doing this: this regex is *the* component that BS4 uses
    # to validate CSS selectors. however, it did not include a dash, meaning
    # that a hude chunk of XML could not be CDD selected with BS4. i just
    # include the dash at the end of the regex
    Tag.tag_name_re = re.compile(r'^[a-z0-9-]+$')

    # this is done here and not at the beginning because we need to modify a
    # dependency - Tag - first.
    from bs4 import BeautifulSoup
    schema = BeautifulSoup(open(schm, 'r').read())
    curriculum = BeautifulSoup(open(curr, 'r').read())
    curriculum = add_numbers(curriculum)
    curriculum = splice(schema, curriculum)
    with open(outf, 'w') as f:
        f.write(str(curriculum))


def get_schema_curricula_pairs(root_dir, courses=['FEWD-001', 'PIP-001']):
    rets = []
    if root_dir[0] == '.':
        root_dir = join(getcwd(), root_dir[2:])
    elif root_dir[0] == '/':
        root_dir = join(getcwd(), root_dir[1:])
    else:
        root_dir = join(getcwd(), root_dir)
    for course in courses:
        versions = [v for v in listdir(join(root_dir, course)) if re.match('^v\d+$', v)]
        # import pdb
        # pdb.set_trace()
        version_paths = [join(root_dir, course, v) for v in versions]
        for v in version_paths:
            triple = (join(v, 'schema.xml'),
                      join(v, 'curriculum.xml'),
                      join(v, 'spliced.xml'))
            rets.append(triple)
    return rets


def main():
    parser = OptionParser("%prog [--root_dir ./lib/curricula]")
    parser.add_option("--root_dir", action="store", default="./lib/curricula")
    (options, args) = parser.parse_args()
    for triplet in get_schema_curricula_pairs(options.root_dir):
        splice_and_save(*triplet)

if __name__ == '__main__':
    main()
