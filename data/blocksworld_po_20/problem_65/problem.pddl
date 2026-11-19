(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue_1 - block
		blue_2 - block
		blue_3 - block
		green_1 - block
		green_2 - block
		green_3 - block
		green_4 - block
		orange_1 - block
		orange_2 - block
		orange_3 - block
		purple_1 - block
		purple_2 - block
		purple_3 - block
		red_1 - block
		red_2 - block
		red_3 - block
		yellow_1 - block
		yellow_2 - block
		yellow_3 - block
		yellow_4 - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable green_4)
		(on yellow_3 green_4)
		(on red_3 yellow_3)
		(on purple_3 red_3)
		(clear purple_3)

		(ontable yellow_2)
		(on yellow_4 yellow_2)
		(on blue_1 yellow_4)
		(clear blue_1)

		(ontable red_1)
		(on green_1 red_1)
		(on purple_1 green_1)
		(clear purple_1)

		(ontable yellow_1)
		(on orange_1 yellow_1)
		(on green_3 orange_1)
		(clear green_3)

		(ontable red_2)
		(on purple_2 red_2)
		(on orange_2 purple_2)
		(clear orange_2)

		(ontable blue_2)
		(on blue_3 blue_2)
		(on orange_3 blue_3)
		(on green_2 orange_3)
		(clear green_2)
	)
	(:goal (and (handempty robot)
		(ontable red_2)
		(on red_1 red_2)
		(on yellow_1 red_1)
		(on blue_3 yellow_1)
		(clear blue_3)

		(ontable purple_1)
		(on blue_1 purple_1)
		(on yellow_3 blue_1)
		(clear yellow_3)

		(ontable purple_3)
		(on yellow_4 purple_3)
		(on red_3 yellow_4)
		(clear red_3)

		(ontable green_3)
		(on orange_2 green_3)
		(on green_4 orange_2)
		(clear green_4)

		(ontable orange_1)
		(on blue_2 orange_1)
		(on green_2 blue_2)
		(clear green_2)

		(ontable purple_2)
		(on green_1 purple_2)
		(on yellow_2 green_1)
		(on orange_3 yellow_2)
		(clear orange_3)
	))
)