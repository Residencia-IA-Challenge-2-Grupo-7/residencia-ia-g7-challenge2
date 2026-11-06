from base.normalizar import (canon, data_no_trecho, dias, diz_gratuito, horas, minutos_abertos, numeros,
                             trecho_no_texto, valor_no_trecho)


def test_numeros_brasileiros():
    assert numeros("Feijoada R$ 49,90") == {49.9}
    assert numeros("1.234,56 e 39.90") == {1234.56, 39.9}
    assert valor_no_trecho(12, "Chopp 300ml ... 12")


def test_horas():
    assert horas("Ter a dom, das 18h às 23h30") == {"18:00", "23:30"}
    assert horas("Mo-Fr 11:00-24:00") == {"11:00", "00:00"}
    assert "12:00" in horas("abre ao meio-dia")
    assert minutos_abertos("18:00", "02:00") == 8 * 60


def test_dias_intervalos_e_negacao():
    assert dias("Terça a domingo, 12h às 22h") == {"ter", "qua", "qui", "sex", "sab", "dom"}
    assert dias("Seg. a sex. 11h-15h") == {"seg", "ter", "qua", "qui", "sex"}
    assert dias("Segunda-feira a sexta-feira") == {"seg", "ter", "qua", "qui", "sex"}
    assert dias("Aberto todos os dias") == {"seg", "ter", "qua", "qui", "sex", "sab", "dom"}
    assert dias("De ter a dom. Fechado às segundas") == {"ter", "qua", "qui", "sex", "sab", "dom"}
    assert dias('"openingHours": "Mo-Fr 11:00-23:00"') == {"seg", "ter", "qua", "qui", "sex"}
    assert dias("Sábados e domingos") == {"sab", "dom"}
    # 'ter' como verbo não é dia
    assert dias("para ter acesso das 8h às 18h") == set()
    assert dias("Domingo à Domingo, 11h - 00h") == {"seg", "ter", "qua", "qui", "sex", "sab", "dom"}
    # barra é ambígua (intervalo ou dois dias): não vira intervalo
    assert dias("Aberto de SEG/SÁB de 12:00 às 20:00") == {"seg", "sab"}


def test_horas_com_h_e_dois_pontos():
    assert horas("das 17h:30 às 23h") == {"17:30", "23:00"}


def test_datas():
    assert data_no_trecho("2026-11-15", "Sábado, 15/11, às 20h")
    assert data_no_trecho("2026-11-15", "15 de novembro de 2026")
    assert data_no_trecho("2026-11-15", '"startDate": "2026-11-15T20:00"')
    assert not data_no_trecho("2026-11-16", "15/11")


def test_trecho_literal():
    texto = canon("Funcionamento:\n Terça a domingo   das 18h às 23h\nRua das Flores")
    assert trecho_no_texto("Terça a domingo das 18h às 23h", texto)
    assert trecho_no_texto("Funcionamento: ... das 18h às 23h", texto)
    assert not trecho_no_texto("Segunda a domingo das 18h às 23h", texto)


def test_ocr_e_distancia_entre_partes():
    from base.normalizar import canon
    texto = canon("cupuaçu c/açaí 3ooml rs 27 5ooml rª34")
    assert trecho_no_texto("CUPUAÇU C/AÇAÍ 300ml R$ 27", texto)
    assert trecho_no_texto("5ooml R$ 34", texto)
    longe = canon("Calabresa" + " x" * 250 + " Grande R$ 55")
    assert not trecho_no_texto("Calabresa ... Grande R$ 55", longe)
    menu = canon("Minas Cheese pão, carne, queijo e molho da casa R$ 35,70 Minas Duplo dois hambúrgueres R$ 31,70")
    assert trecho_no_texto("Minas Cheese ... R$ 35,70", menu)
    assert not trecho_no_texto("Minas Cheese ... R$ 31,70", menu)  # outro preço no meio


def test_gratuito():
    assert diz_gratuito("Entrada franca")
    assert diz_gratuito("Acesso gratuito ao parque")
    assert not diz_gratuito("Parque ao ar livre")
