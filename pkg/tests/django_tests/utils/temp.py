class FakeDes:
    def __get__(self, instance, owner):
        print('_get_r called')

        return instance
    def __set__(self, instance, value):
        pass

class Fake:

    def __getattr__(self, item):
        print(f'_getattr called:{item}')
        setattr(type(self), item, FakeDes())
        return getattr(self, item)

if __name__ == '__main__':
    f = Fake()
    print(getattr(f, 'xval'))
    print(getattr(f, 'xval'))
    setattr(f, 'gf', 'fd')
    print(getattr(f, 'gf'))
    print(hasattr(f, 'gsf'))

    print(f.xval)