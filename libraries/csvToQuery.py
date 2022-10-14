import sql
import ssau_parser
import datetime

def convert(file):
	lessons = []
	teachers = {}
	teacher_columns = ["surname","name","midname"]
	groupId = None
	with open(f'{file}.csv', encoding='utf-8') as f:
		day = datetime.datetime(2022,1,1)
		numInDay = 1
		for i, line in enumerate(f.readlines()):
			line = line.replace("\n","")
			lesson = line.split(";")
			if i == 0:
				groupId = line[-1]
				continue
			if len(lesson) != 8:
				print(f'Incorrect line N{i}')
				continue
			
			teacher = lesson[5]
			teacher_info = ssau_parser.findInRasp(teacher) if teacher != "" else None;
			if teacher_info != None:
				teacherId = teacher_info['id']
				teacher_name = teacher_info['text'].split()
				teachers[teacherId] = dict(zip(teacher_columns, teacher_name))
				teacher = teacherId
			else:
				teacher = None
				
			date = datetime.datetime.strptime(lesson[0],'%d.%m.%Y')
			begin = datetime.datetime.strptime(f'{lesson[0]} {lesson[3]}','%d.%m.%Y %H:%M')
			end = datetime.datetime.strptime(f'{lesson[0]} {lesson[4]}','%d.%m.%Y %H:%M')
			
			if day < date:
				day = date
				numInDay = 1
			else:
				numInDay += 1
				
			lessons.append({
			'numInDay' : numInDay,
			'type' : lesson[1],
			'name' : lesson[2],
			'groupId' : groupId,
			'begin' : begin,
			'end' : end,
			'teacherId' : teacherId,
			'place' : lesson[6],
			'add_info':lesson[7]}
			)
		
		teachers_list = []
		for tId, t in teachers.items():
			td = t
			td['teacherId'] = tId
			teachers_list.append(td)
			
		return groupId, lessons, teachers_list

if __name__ == "__main__":			
	groupId, lessons, teachers = convert('rasp')
	l9lk = sql.L9LK(open("pass.txt").read())
	sh = sql.Shedule_DB(l9lk)
	for t in teachers:
		l9lk.db.insert(sql.Shedule_DB.teachers_table, t)
		
	for l in lessons:
		l9lk.db.insert(sql.Shedule_DB.lessons_table, l)
