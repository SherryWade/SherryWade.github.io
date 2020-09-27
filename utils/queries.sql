# Select Shows for a specific year and month
select
	*
from
	event
where
	YEAR(start_time) = 2020 AND MONTH(start_time) = 5
limit 10;


INSERT INTO
    user
    (username, email, password_hash)
VALUES
    ('brandon.walker', 'brandon@bethwalker.com', ''),
    ('admin', 'b@charleston.ai', '');