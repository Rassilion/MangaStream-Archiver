# MangaStream Archiver
Python 2.7 program for downloading new releases from MangaStream. Its working but doesn't tested fully

- data is in sqllite database
- creates manga and chapter list in database
- special characters removed from names (slug)
- downloads new chapters from site and zip

## Database model

##### Manga

- name
- url
- chapters <- Chapter


##### Chapter

- name
- url
- cdn_id
- manga -> Manga
- downloaded
- page
