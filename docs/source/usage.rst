Kullanım
=======

Web Arayüzü
----------

1. Hash Oluşturma
~~~~~~~~~~~~~~~~

* Ana sayfada "Generate Hash" bölümüne gidin
* Şifrenizi girin veya rastgele şifre oluşturun
* "Generate" butonuna tıklayın

2. Hash Kırma
~~~~~~~~~~~~

* "Crack Hash" bölümüne hash değerini girin
* Maksimum şifre uzunluğunu ayarlayın
* "Start Cracking" butonuna tıklayın
* İlerlemeyi gerçek zamanlı olarak takip edin

API Kullanımı
-----------

Hash Oluşturma
~~~~~~~~~~~~

.. code-block:: python

    import requests

    response = requests.post('http://localhost:5000/generate_hash', 
                           data={'password': 'test123'})
    print(response.json())

Hash Kırma
~~~~~~~~~

.. code-block:: python

    response = requests.post('http://localhost:5000/crack_hash',
                           data={'hash': '202cb962ac59075b964b07152d234b70'})
    print(response.json()) 