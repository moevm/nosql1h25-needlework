# Сценарий использования

## Главная страница
**Действующее лицо:** пользователь

### Основной сценарий:
1. Пользователь заходит на сайт и попадает на главную страницу.
2. На главной странице отображаются схемы для вышивания или вязания от всех пользователей. По умолчанию схемы сортируются по дате добавления (новые сверху).
3. Слева находится панель с фильтрами для сортировки и поиска схем:
   - Количество цветов (от ... до ...).
   - Выбор цветов (список).
   - Дата публикации (от ... до ...).
   - Тип работы (вязание, вышивка).
   - Сортировка:
     - По лайкам.
     - По дате публикации.
     - По длине используемой нити.
     - По количеству цветов.
   - Порядок сортировки:
     - По умолчанию (по возрастанию).
     - Обратный (по убываниию).
4. Пользователь может применять фильтры и сортировку для удобного просмотра схем.

### Альтернативный сценарий:
- Если пользователь не авторизован, он может просматривать схемы, но не может лайкать, комментировать или загружать свои схемы.

---

## Панель навигации
**Действующее лицо:** пользователь

### Основной сценарий:
1. В верхней части всех страниц сайта находится навигационная панель.
2. На панели отображаются следующие элементы:
   - **Кнопка домашней страницы:** Переход на главную страницу.
   - **Кнопка "Создать новый пост":** Видна только авторизованным пользователям. При нажатии открывается страница для загрузки новой схемы.
   - **Кнопка выбора языка:** По умолчанию выбран английский язык. Пользователь может изменить язык интерфейса.
   - **Иконка пользователя:** Видна всем пользователям. При нажатии авторизованным пользователем выполняется переход на страницу пользователя. При нажатии неавторизованным пользователем выполняется переход на страницу авторизации.
   - **Кнопка "Выйти":** Видна только авторизованным пользователям. При нажатии пользователь выходит из аккаунта.
   - **Кнопки для администратора (видны только админам):**
     - **Импорт/Экспорт:** Направляет на страницу импорта/экспорта данных.
     - **Статистика:** Переход на страницу статистики.
     - **Панель администратора:** Переход на страницу администрации.

### Альтернативные сценарии:
- Для неавторизованных пользователей:
  - Кнопка "Создать новый пост" не отображается.
  - Кнопка "Выйти" отсутствует.
  - Кнопки импорта, экспорта и статистики не отображаются.
- Для авторизованных пользователей:
  - Если пользователь не администратор, кнопки импорта/экспорта, статистики и панель администратора не отображаются.
- Для администраторов:
  - Все кнопки навигации (включая импорт/экспорт, статистику и панель администратора) доступны.

---

## Авторизация
**Действующее лицо:** пользователь

### Основной сценарий:
1. Пользователь нажимает на иконку пользователя.
2. Открывается окно авторизации и регистрации.
3. В левой части окна пользователь может ввести:
   - Логин.
   - Пароль.
4. Пользователь нажимает кнопку "Login".
5. Если данные верны, пользователь авторизуется и получает доступ к функционалу (лайки, комментарии, загрузка схем).

### Альтернативный сценарий:
- Если данные введены некорректно, пользователь видит сообщение об ошибке (например, "Неверный логин или пароль").

## Регистрация
**Действующее лицо:** пользователь

### Основной сценарий:
1. Пользователь нажимает на иконку пользователя.
2. Открывается окно входа и регистрации.
3. В правой части окна пользователь вводит:
   - Логин.
   - Имя.
   - Фамилию.
   - Пароль (два раза для подтверждения).
4. Пользователь нажимает кнопку "Register".
5. Если данные введены корректно, создаётся новый аккаунт, и пользователь автоматически авторизуется.

### Альтернативный сценарий:
- Если данные введены некорректно (например, пароли не совпадают), пользователь видит сообщение об ошибке.
- Если логин уже занят, пользователь видит сообщение об ошибке (например, "Такой пользователь уже существует").
---

## Страница пользователя
**Действующее лицо:** пользователь

### Основной сценарий:
1. Пользователь находится на своей странице.
2. На странице отображается:
   - Имя и фамилия пользователя.
   - Дата регистрации.
   - Количество опубликованных схем (постов).
   - Схемы, загруженные пользователем (только его схемы).
3. Слева находится панель с фильтрами для сортировки и поиска схем:
   - Количество цветов (от ... до ...).
   - Выбор цветов (список).
   - Дата публикации (от ... до ...).
   - Тип работы (вязание, вышивка).
   - Сортировка:
     - По лайкам.
     - По дате публикации.
     - По длине используемой нити.
     - По количеству цветов.
   - Порядок сортировки:
     - По умолчанию (по возрастанию).
     - Обратный (по убываниию).
4. В блоке с информацией о пользователе отображается кнопка "Edit User".
5. Пользователь нажимает на кнопку "Edit User" и переходит на страницу редактирования профиля.

### Альтернативный сценарий: Не на своей странице
1. Пользователь находится на странице другого пользователя.
2. Все элементы страницы (фильтры, сортировка, информация о пользователе, схемы) отображаются так же, как и на своей странице.
3. **Отсутствует кнопка "Edit User"** в блоке с информацией о пользователе.

---

## Редактирование данных пользователя
**Действующее лицо:** авторизованный пользователь

### Основной сценарий:
1. Пользователь находится на своей странице.
2. Пользователь нажимает на кнопку "Edit User".
3. Пользователь перенаправляется на страницу редактирования профиля.
4. Страница редактирования разделена на две части:
   - **Левая часть:** Изменение личных данных.
     - Поля для редактирования:
       - Логин.
       - Имя.
       - Фамилия.
     - Кнопка "Apply changes".
   - **Правая часть:** Изменение пароля.
     - Поля для редактирования:
       - Старый пароль.
       - Новый пароль.
       - Подтверждение нового пароля.
     - Кнопка "Change password".

### Альтернативный сценарий:
- Отменить редактирование можно перейдя на любую другую страницу.
- Если логин уже занят, пользователь видит сообщение об ошибке (например, "Этот логин уже используется").
- Если старый пароль введён неверно, пользователь видит сообщение об ошибке (например, "Неверный старый пароль").

---

## Поиск схем
**Действующее лицо:** пользователь

### Основной сценарий:
1. Пользователь вбивает в строку поиска нужное ему название схемы.
2. Сайт ищет в каталоге нужную схему по названию и выдает ее пользователю.

### Альтернативный сценарий:
1. Пользователь выбирает нужные ему фильтры:
- Количество цветов (от ... до ...).
   - Выбор цветов (список).
   - Дата публикации (от ... до ...).
   - Тип работы (вязание, вышивка).
   - Сортировка:
     - По лайкам.
     - По дате публикации.
     - По длине используемой нити.
     - По количеству цветов.
   - Порядок сортировки:
     - По умолчанию (по возрастанию).
     - Обратный (по убываниию).
2. Пользователь вбивает в строку поиска частичное описание нужной ему схемы: сайт ищет подходящие схемы и выдает их.

---

## Открытие определенной схемы
**Действующее лицо:** пользователь

### Основной сценарий:
1. Пользователь, найдя нужную ему схему, нажимает кнопку **View**.
2. Сайт открывает окно просмотра этой схемы.

---

## Просмотр увеличенной версии схемы
**Действующее лицо:** пользователь

### Основной сценарий:
1. Пользователь может нажать на картинку, чтобы открыть увеличенную версию изображения.

---

## Оценивание поста
**Действующее лицо:** авторизованный пользователь

### Основной сценарий:
1. Если пользователь авторизован, он может поставить посту лайк/дизлайк, нажав на определенную кнопку.

### Альтернативный сценарий:
1. Если пользователь не авторизован, то при попытке оценки выдаст ошибку "Недоступно неавторизованным пользователям".

---

## Комментирование
**Действующее лицо:** авторизованный пользователь

### Основной сценарий:
1. Если пользователь авторизован, то он может написать комментарий к схеме и опубликовать его, нажав на кнопку **Post**.

### Альтернативный сценарий:
1. Если пользователь не авторизован, то он не может опубликовать свой комментарий, у него нет кнопки **Post**.

---

## Редактирование схемы
**Действующее лицо:** авторизованный пользователь (автор схемы)

### Основной сценарий:
1. Если пользователь авторизован и является автором схемы, он может редактировать свой пост, нажав на кнопку **Edit**.
2. В режиме редактирования автор может изменить название, описание, необходимые расходные материалы, свой комментарий и картинки.
3. Автор сохраняет изменения, нажав на кнопку **Apply Changes**.

### Альтернативный сценарий:
1. Если пользователь не авторизован или авторизован, но не является автором, то он не может редактировать пост, у него нет кнопки **Edit**.

---

## Удаление схемы
**Действующее лицо:** авторизованный пользователь (автор/администратор)

### Основной сценарий:
1. При просмотре определенного поста, если пользователь является автором или администратором, он может удалить этот пост, нажав на кнопку **Delete**.

### Альтернативный сценарий:
1. Если пользователь не авторизован или авторизован, но не является автором или администратором, то он не может удалить пост, у него нет кнопки **Delete**.

---

## Страница загрузки новой схемы
**Действующее лицо:** авторизованный пользователь

### Основной сценарий:
1. Пользователь авторизован и нажимает на кнопку "Создать новый пост" в верхней навигационной панели.
2. Пользователь перенаправляется на страницу загрузки новой схемы.
3. На странице отображается форма для загрузки схемы:
   - **Поле "Название схемы":** Пользователь вводит название схемы.
   - **Поле "Описание схемы":** Пользователь пишет описание схемы (например, материалы, сложность, инструкции).
   - **Выбор типа работы:** Пользователь выбирает тип работы из списка:
     - Вязание.
     - Вышивание.
   - **Поле "Комментарий автора":** Пользователь может добавить дополнительный комментарий.
   - **Поле для загрузки изображения:** Пользователь загружает изображение схемы (например, фотография готового изделия или пример).
   - **Поле для загрузки файла схемы:** Пользователь загружает файл схемы.
4. После заполнения всех полей пользователь нажимает кнопку "Post Scheme".
5. Если все данные введены корректно, схема публикуется и появляется в списке на главной странице и на странице пользователя.

### Альтернативный сценарий:
- Если пользователь не заполнил обязательные поля (например, название схемы или файл схемы), появляется сообщение об ошибке (например, "Заполните все обязательные поля").
- Если загруженный файл не соответствует требованиям (например, слишком большой размер или недопустимый формат), появляется сообщение об ошибке (например, "Недопустимый формат файла").

---

## Импорт/Экспорт
**Действующее лицо:** авторизованный пользователь (администратор)

### Основной сценарий:
1. Пользователь на панели навигации нажимает на кнопку **Import/Export**.
2. Сайт перенаправляет его на страницу импорта и экспорта.
3. Пользователь может нажать на кнопку Import DB и импортировать данные.
4. Пользователь может нажать на кнопку Export DB и экспортировать данные.

### Альтернативный сценарий:
1. Если пользователь не авторизован или авторизован, но не является админом, он не видит кнопки **Import/Export** и не может выполнить импорт или экспорт данных с сайта.

---

## Панель администратора (взаимодействие с пользователями)
**Действующее лицо:** авторизованный пользователь (администратор)

### Основной сценарий:
1. Пользователь на панели навигации нажимает на кнопку **Admin panel**.
2. Сайт перенаправляет его на страницу панели администратора, где сразу по умолчанию показываются все пользователи сайта.
3. Администратор нажимает на кнопку **Block** и блокирует определенного пользователя.

### Альтернативный сценарий:
1. Если выбранный пользователь имеет статус *Admin*, администратор нажимает на кнопку **Demote**, выбранный пользователь понижается, у него забирают статус *Admin* и выдают статус *User*.
2. Если выбранный пользователь имеет статус *User*, администратор нажимает на кнопку **Promote**, выбранный пользователь повышается, у него забирают статус *User* и выдают статус *Admin*.

---

## Панель администратора (взаимодействие со схемами)
**Действующее лицо:** авторизованный пользователь (администратор)

### Основной сценарий:
1. Пользователь на панели навигации нажимает на кнопку **Admin panel**.
2. Сайт перенаправляет его на страницу панели администратора, где сразу по умолчанию показываются все пользователи сайта.
3. Администратор выбирает параметр *Schemes*.
4. Сайт показывает все схемы, имеющиеся на сайте и всю информацию о них (тип схемы, никнейм создателя, дата создания, дата обновления, общая длина расходных материалов, количество лайков, количество дизлайков и количество комментариев), а также доступные опции просмотр и удаление.
5. Администратор нажимает кнопку **View** и попадает на страницу просмотра схемы.

### Альтернативный сценарий:
1. Администратор нажимает кнопку **Delete** и происходит удаление определенной схемы.

---

## Получение статистики
**Действующее лицо:** авторизованный пользователь (администратор)

### Основной сценарий:
1. Пользователь на панели навигации нажимает на кнопку **Statistics**.
2. Сайт перенаправляет его на страницу статистики.
3. Администратор выбирает два параметра по оси X и по оси Y, по которым будет строиться график статистики.
4. Сайт предоставляет администратору полную статистику по всем имеющимся схемам.

### Альтернативный сценарий:
1. Администратор также выбирает необходимые ему фильтры, сайт отбирает подходящие схемы и на их основе строит график по выбранным параметрам.
