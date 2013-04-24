import MySQLdb

def is_partner_program(assetId):
    connection = MySQLdb.connect('reporting2.istockphoto.com', 'maint', 'ngTX6Kupa$c', 'istockphoto')
    cursor = connection.cursor()
    query = 'select Collections from AbstractFile where ID = %d' % assetId
    cursor.execute(query)
    data = cursor.fetchone()
    return data[0].find('GettyDistribution') != -1
