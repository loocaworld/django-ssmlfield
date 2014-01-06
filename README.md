
django-ssmlfield
================

Super Simple Multilingual Field for Django

=====
Usage
=====

models.py

	class Test(models.Model):
		desc = SSMLTextField()

You can do like this

	a = Test()
	a.desc['ko'] = 'korean string'
	a.desc['ja'] = 'japanese string'
	a.save()

	print a.desc['ko']

	