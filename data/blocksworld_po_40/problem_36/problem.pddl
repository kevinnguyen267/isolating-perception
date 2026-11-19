(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue_1 - block
		blue_2 - block
		blue_3 - block
		blue_4 - block
		blue_5 - block
		blue_6 - block
		blue_7 - block
		green_1 - block
		green_2 - block
		green_3 - block
		green_4 - block
		green_5 - block
		green_6 - block
		green_7 - block
		orange_1 - block
		orange_2 - block
		orange_3 - block
		orange_4 - block
		orange_5 - block
		orange_6 - block
		purple_1 - block
		purple_2 - block
		purple_3 - block
		purple_4 - block
		purple_5 - block
		purple_6 - block
		purple_7 - block
		red_1 - block
		red_2 - block
		red_3 - block
		red_4 - block
		red_5 - block
		red_6 - block
		yellow_1 - block
		yellow_2 - block
		yellow_3 - block
		yellow_4 - block
		yellow_5 - block
		yellow_6 - block
		yellow_7 - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable red_6)
		(on green_3 red_6)
		(on purple_5 green_3)
		(on purple_3 purple_5)
		(on green_4 purple_3)
		(on orange_2 green_4)
		(on green_5 orange_2)
		(clear green_5)

		(ontable yellow_1)
		(on red_4 yellow_1)
		(on red_5 red_4)
		(on yellow_7 red_5)
		(on green_1 yellow_7)
		(on orange_4 green_1)
		(on blue_5 orange_4)
		(clear blue_5)

		(ontable yellow_5)
		(on orange_5 yellow_5)
		(on yellow_4 orange_5)
		(on blue_6 yellow_4)
		(on yellow_3 blue_6)
		(on orange_3 yellow_3)
		(on blue_1 orange_3)
		(clear blue_1)

		(ontable blue_2)
		(on green_2 blue_2)
		(on orange_6 green_2)
		(on purple_2 orange_6)
		(on yellow_2 purple_2)
		(on purple_7 yellow_2)
		(clear purple_7)

		(ontable red_3)
		(on purple_1 red_3)
		(on green_6 purple_1)
		(on red_2 green_6)
		(on green_7 red_2)
		(on purple_4 green_7)
		(clear purple_4)

		(ontable red_1)
		(on orange_1 red_1)
		(on yellow_6 orange_1)
		(on blue_7 yellow_6)
		(on blue_3 blue_7)
		(on purple_6 blue_3)
		(on blue_4 purple_6)
		(clear blue_4)
	)
	(:goal (and (handempty robot)
		(ontable orange_2)
		(on blue_6 orange_2)
		(on green_2 blue_6)
		(on green_5 green_2)
		(on yellow_5 green_5)
		(on purple_7 yellow_5)
		(clear purple_7)

		(ontable red_3)
		(on red_6 red_3)
		(on orange_3 red_6)
		(on red_5 orange_3)
		(on yellow_1 red_5)
		(on blue_5 yellow_1)
		(clear blue_5)

		(ontable green_6)
		(on purple_5 green_6)
		(on orange_1 purple_5)
		(on blue_3 orange_1)
		(on blue_2 blue_3)
		(on blue_7 blue_2)
		(on red_1 blue_7)
		(clear red_1)

		(ontable yellow_3)
		(on blue_1 yellow_3)
		(on orange_5 blue_1)
		(on green_3 orange_5)
		(on purple_1 green_3)
		(on green_4 purple_1)
		(on purple_4 green_4)
		(clear purple_4)

		(ontable orange_4)
		(on purple_3 orange_4)
		(on red_4 purple_3)
		(on green_7 red_4)
		(on green_1 green_7)
		(on yellow_4 green_1)
		(on blue_4 yellow_4)
		(clear blue_4)

		(ontable red_2)
		(on orange_6 red_2)
		(on yellow_2 orange_6)
		(on purple_6 yellow_2)
		(on purple_2 purple_6)
		(on yellow_6 purple_2)
		(on yellow_7 yellow_6)
		(clear yellow_7)
	))
)